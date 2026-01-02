import asyncio
from typing import Dict, List, Optional
from models import (
    Section, Connection, TrainType, Train, Wagon, ScheduleEntry, RailBlock
)

class SimulationEngine:
    """Decoupled simulation engine that handles train movement and safety logic."""
    
    def __init__(
        self,
        sections: List[Section],
        connections: List[Connection],
        train_types: List[TrainType],
        trains: List[Train],
        blocks: List[RailBlock] = [],
        schedules: Dict[int, List[ScheduleEntry]] = {}
    ):
        # Use dicts for O(1) access by ID
        self.sections: Dict[int, Section] = {s.section_id: s for s in sections}
        self.train_types: Dict[int, TrainType] = {tt.train_type_id: tt for tt in train_types}
        self.trains: Dict[int, Train] = {t.train_id: t for t in trains}
        self.schedules: Dict[int, List[ScheduleEntry]] = schedules
        
        # Map section_id -> block_id (optional)
        self.section_to_block: Dict[int, int] = {b.section_id: b.block_id for b in blocks}
        
        # Build adjacency list for the network graph
        self.network: Dict[int, List[Connection]] = {}
        for conn in connections:
            if conn.from_section_id not in self.network:
                self.network[conn.from_section_id] = []
            self.network[conn.from_section_id].append(conn)

        # Initialize wagons for each train
        self.wagons: Dict[int, Wagon] = {}  # wagon_id -> Wagon
        self.train_wagons: Dict[int, List[int]] = {}  # train_id -> [wagon_ids]
        self._initialize_wagons()

        # Initialize section occupancy
        self._initialize_occupancy()

        # Async lock to protect engine state
        self.lock = asyncio.Lock()

    def _initialize_wagons(self):
        """Create Wagon objects for each train based on `num_wagons`."""
        wagon_id_counter = 1000
        for train in self.trains.values():
            num_wagons = getattr(train, 'num_wagons', 1)
            num_wagons = max(1, min(15, num_wagons))  # Clamp tra 1 e 15
            
            self.train_wagons[train.train_id] = []
            for wagon_idx in range(num_wagons):
                wagon = Wagon(
                    wagon_id=wagon_id_counter,
                    train_id=train.train_id,
                    wagon_index=wagon_idx,
                    section_id=train.current_section_id,
                    position_offset=train.position_offset
                )
                self.wagons[wagon_id_counter] = wagon
                self.train_wagons[train.train_id].append(wagon_id_counter)
                wagon_id_counter += 1

    def _initialize_occupancy(self):
        """Set initial `is_occupied` on sections using current wagon positions."""
        # Reset occupancy
        for section in self.sections.values():
            section.is_occupied = False
        
        # Marca le sezioni come occupate se contengono almeno un vagone
        occupied_sections = set()
        for wagon in self.wagons.values():
            if wagon.section_id:
                occupied_sections.add(wagon.section_id)
        
        for section_id in occupied_sections:
            if section_id in self.sections:
                self.sections[section_id].is_occupied = True

    async def run_tick(self, dt: float):
        """
        Avanza la simulazione di un intervallo 'dt' (in secondi).
        Questo è il ciclo principale del motore.
        Sposta i vagoni individuali invece che i treni interi.
        """
        async with self.lock:
            for train in self.trains.values():
                if train.status != 'Moving':
                    continue

                train_type = self.train_types[train.train_type_id]
                speed_sec_per_sec = train_type.cruising_speed / 60.0
                distance_moved = speed_sec_per_sec * dt

                # Sposta i vagoni in ordine inverso (dalla coda alla testa)
                wagon_ids = self.train_wagons.get(train.train_id, [])
                for wagon_id in reversed(wagon_ids):
                    wagon = self.wagons[wagon_id]
                    if wagon.section_id is None:
                        continue

                    wagon.position_offset += distance_moved

                    # Transition logic between sections
                    while wagon.position_offset >= 1.0:
                        current_section = self.sections.get(wagon.section_id)
                        if not current_section:
                            break

                        # Find next active section
                        next_section = self._find_next_active_section(current_section.section_id)

                        if not next_section:
                            # Fine del binario
                            wagon.position_offset = 0.99
                            train.status = 'Stopped'
                            break

                        # If next section is occupied stop the train
                        if next_section.is_occupied:
                            wagon.position_offset = 0.99
                            train.status = 'Stopped'
                            break

                        # Transizione approvata
                        wagon.position_offset -= 1.0
                        wagon.section_id = next_section.section_id

                # Update section occupancy and sync train position to first wagon
                self._update_section_occupancy()
                if wagon_ids:
                    first_wagon = self.wagons[wagon_ids[0]]
                    train.current_section_id = first_wagon.section_id or train.current_section_id
                    train.position_offset = first_wagon.position_offset

    def _update_section_occupancy(self):
        """Update `is_occupied` flag for all sections based on wagon positions."""
        for section in self.sections.values():
            section.is_occupied = False

        for wagon in self.wagons.values():
            if wagon.section_id and wagon.section_id in self.sections:
                self.sections[wagon.section_id].is_occupied = True

    async def add_trains(self, trains: List[Train]):
        """Add trains to the engine and create their wagons."""
        async with self.lock:
            wagon_id_counter = max([w.wagon_id for w in self.wagons.values()] or [1000], default=1000) + 1
            
            for t in trains:
                if t.train_id in self.trains:
                    continue
                self.trains[t.train_id] = t
                
                # Create wagons for this train
                num_wagons = max(1, min(15, getattr(t, 'num_wagons', 1)))
                self.train_wagons[t.train_id] = []
                
                for wagon_idx in range(num_wagons):
                    wagon = Wagon(
                        wagon_id=wagon_id_counter,
                        train_id=t.train_id,
                        wagon_index=wagon_idx,
                        section_id=t.current_section_id,
                        position_offset=t.position_offset
                    )
                    self.wagons[wagon_id_counter] = wagon
                    self.train_wagons[t.train_id].append(wagon_id_counter)
                    wagon_id_counter += 1
                
                self._update_section_occupancy()

    async def get_sections_state(self) -> List[Section]:
        """Return state of all sections (including occupancy and coords)."""
        async with self.lock:
            return [s.model_copy() for s in self.sections.values()]

    async def get_connections_state(self) -> List[Connection]:
        """Return all network connections with their `is_active` state."""
        async with self.lock:
            conns: List[Connection] = []
            for out_list in self.network.values():
                for c in out_list:
                    conns.append(c)
            return [c.model_copy() for c in conns]

    async def get_blocks_state(self) -> List[RailBlock]:
        """Return a list of RailBlock objects if block mapping was provided."""
        # This engine only keeps a mapping if blocks were passed into __init__
        async with self.lock:
            blocks: List[RailBlock] = []
            # self.section_to_block maps section_id -> block_id
            for section_id, block_id in getattr(self, 'section_to_block', {}).items():
                blocks.append(RailBlock(block_id=block_id, block_name=f"block_{block_id}", section_id=section_id))
            return blocks

    async def get_wagons_state(self) -> List[Wagon]:
        """Return state of all wagons."""
        async with self.lock:
            return [w.model_copy() for w in self.wagons.values()]

    def _find_next_active_section(self, from_section_id: int) -> Optional[Section]:
        """Find the next section reachable from `from_section_id` following an active connection."""
        possible_connections = self.network.get(from_section_id, [])
        active_connections = [c for c in possible_connections if c.is_active]

        if not active_connections:
            return None # Nessun percorso attivo
        
        # Nota: si assume che solo una connessione possa essere attiva
        # per qualsiasi sezione (incluso lo scambio)
        next_section_id = active_connections[0].to_section_id
        return self.sections.get(next_section_id)

    async def set_switch_position(self, switch_section_id: int, target_to_section_id: int):
        """Set the active connection for a switch section (switch control)."""
        async with self.lock:
            switch_section = self.sections.get(switch_section_id)

            # Validazione
            if not switch_section:
                raise ValueError(f"Section {switch_section_id} does not exist.")
            if not switch_section.is_switch:
                raise ValueError(f"Section {switch_section_id} is not a switch.")
            if switch_section.is_occupied:
                raise ValueError(f"Cannot move switch {switch_section_id}: section is occupied.")

            possible_connections = self.network.get(switch_section_id, [])
            target_found = False

            for conn in possible_connections:
                if conn.to_section_id == target_to_section_id:
                    conn.is_active = True
                    target_found = True
                else:
                    # Deactivate all other exits
                    conn.is_active = False
            
            if not target_found:
                raise ValueError(f"Target connection {target_to_section_id} is not valid for switch {switch_section_id}.")

    async def get_all_trains_state(self) -> List[Train]:
        """Thread-safe method to retrieve the state of all trains."""
        async with self.lock:
            # Ritorna una copia per evitare problemi di mutazione
            return [train.model_copy() for train in self.trains.values()]