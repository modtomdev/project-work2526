import asyncio
from typing import Dict, List, Optional
from models import (
    Section, Connection, TrainType, Train, ScheduleEntry, RailBlock
)
from datetime import datetime, timedelta

class SimulationEngine:
    """
    Motore di simulazione disaccoppiato che gestisce la logica
    del movimento dei treni e la sicurezza.
    """
    
    def __init__(
        self,
        sections: List[Section],
        connections: List[Connection],
        train_types: List[TrainType],
        trains: List[Train],
        blocks: List[RailBlock] = [],
        schedules: Dict[int, List[ScheduleEntry]] = {}
    ):
        # Utilizzo di dizionari per un accesso O(1) rapido tramite ID
        self.sections: Dict[int, Section] = {s.section_id: s for s in sections}
        self.train_types: Dict[int, TrainType] = {tt.train_type_id: tt for tt in train_types}
        self.trains: Dict[int, Train] = {t.train_id: t for t in trains}
        self.schedules: Dict[int, List[ScheduleEntry]] = schedules
        
        # Mappa per trovare le sezioni di un blocco (non usata in questa logica base)
        self.section_to_block: Dict[int, int] = {b.section_id: b.block_id for b in blocks}
        
        # Costruisce il grafo della rete per una navigazione efficiente
        self.network: Dict[int, List[Connection]] = {}
        for conn in connections:
            if conn.from_section_id not in self.network:
                self.network[conn.from_section_id] = []
            self.network[conn.from_section_id].append(conn)

        # Inizializza l'occupazione delle sezioni
        self._initialize_occupancy()

        # Lock per la concorrenza tra il tick e le chiamate API
        self.lock = asyncio.Lock()

    def _initialize_occupancy(self):
        """Imposta lo stato 'is_occupied' iniziale per le sezioni dei treni."""
        occupied_sections = {t.current_section_id for t in self.trains.values()}
        for section_id in occupied_sections:
            if section_id in self.sections:
                self.sections[section_id].is_occupied = True

    async def run_tick(self, dt: float):
        """
        Avanza la simulazione di un intervallo 'dt' (in secondi).
        Questo è il ciclo principale del motore.
        """
        async with self.lock:
            for train in self.trains.values():
                if train.status != 'Moving':
                    continue # Questo treno non si sta muovendo

                train_type = self.train_types[train.train_type_id]
                
                # Calcola la velocità in sezioni/secondo
                speed_sec_per_sec = train_type.cruising_speed / 60.0
                
                # Calcola la distanza percorsa in questo tick (come frazione di sezione)
                distance_moved = speed_sec_per_sec * dt
                train.position_offset += distance_moved

                # --- Logica di Transizione di Sezione ---
                if train.position_offset >= 1.0:
                    current_section = self.sections[train.current_section_id]
                    
                    # 1. Trova la prossima sezione in base agli scambi
                    next_section = self._find_next_active_section(current_section.section_id)

                    if not next_section:
                        # Fine del binario o scambio non impostato
                        train.status = 'Stopped'
                        train.position_offset = 0.99 # Fermati alla fine
                        continue

                    # 2. Logica di Sicurezza (Controllo Blocco/Occupazione)
                    if next_section.is_occupied:
                        # Collisione imminente! Fermo il treno.
                        train.status = 'Stopped'
                        train.position_offset = 0.99 # Fermati prima della sezione
                    else:
                        # Transizione approvata
                        current_section.is_occupied = False # Libera la vecchia sezione
                        next_section.is_occupied = True    # Occupa la nuova
                        
                        train.current_section_id = next_section.section_id
                        # Riporta l'offset rimanente
                        train.position_offset -= 1.0 
                        
            # TODO: Gestire la logica degli orari (ScheduleEntry)
            # (Es. cambiare stato da 'Scheduled' a 'Moving' o da 'Moving' a 'Stopped')

    def _find_next_active_section(self, from_section_id: int) -> Optional[Section]:
        """
        Trova la prossima sezione collegata che ha una connessione 'is_active'.
        Per le sezioni normali, ci sarà solo una.
        Per gli scambi, ne troverà una sola (quella impostata).
        """
        possible_connections = self.network.get(from_section_id, [])
        active_connections = [c for c in possible_connections if c.is_active]

        if not active_connections:
            return None # Nessun percorso attivo
        
        # Nota: si assume che solo una connessione possa essere attiva
        # per qualsiasi sezione (incluso lo scambio)
        next_section_id = active_connections[0].to_section_id
        return self.sections.get(next_section_id)

    async def set_switch_position(self, switch_section_id: int, target_to_section_id: int):
        """
        Imposta la connessione attiva per una sezione di scambio.
        Questa è la logica di controllo degli scambi.
        """
        async with self.lock:
            switch_section = self.sections.get(switch_section_id)

            # Validazione
            if not switch_section:
                raise ValueError(f"La sezione {switch_section_id} non esiste.")
            if not switch_section.is_switch:
                raise ValueError(f"La sezione {switch_section_id} non è uno scambio.")
            if switch_section.is_occupied:
                raise ValueError(f"Impossibile muovere lo scambio {switch_section_id}: è occupato.")

            possible_connections = self.network.get(switch_section_id, [])
            target_found = False

            for conn in possible_connections:
                if conn.to_section_id == target_to_section_id:
                    conn.is_active = True
                    target_found = True
                else:
                    # Disattiva tutte le altre uscite
                    conn.is_active = False
            
            if not target_found:
                raise ValueError(f"Connessione a {target_to_section_id} non valida per lo scambio {switch_section_id}.")

    async def get_all_trains_state(self) -> List[Train]:
        """Metodo thread-safe per ottenere lo stato di tutti i treni."""
        async with self.lock:
            # Ritorna una copia per evitare problemi di mutazione
            return [train.model_copy() for train in self.trains.values()]