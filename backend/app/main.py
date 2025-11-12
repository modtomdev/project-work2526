import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Optional

from models import Train, Section, Connection, TrainType, SwitchSetPayload
from simulation import SimulationEngine

app = FastAPI(
    title="TrenoSim - Simulatore di Rete Ferroviaria",
    description="API per il controllo e monitoraggio di una simulazione ferroviaria.",
    version="1.0.0"
)

# Istanza globale del motore (verrà inizializzata allo startup)
engine: Optional[SimulationEngine] = None

# --- Gestore WebSocket ---
class ConnectionManager:
    """Gestisce le connessioni WebSocket attive per il broadcast."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        """Invia dati JSON a tutti i client connessi."""
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()


# --- Loop di Simulazione (Task in Background) ---
async def simulation_loop(tick_rate_hz: int = 10, sim_speed_multiplier: int = 5):
    """
    Il ciclo principale che fa avanzare il motore di simulazione
    e trasmette gli aggiornamenti.
    """
    if engine is None:
        print("Errore: Motore non inizializzato.")
        return

    # dt è l'intervallo di tempo *reale* tra i tick
    real_dt = 1.0 / tick_rate_hz
    # sim_dt è l'intervallo di tempo *simulato* (accelerato)
    sim_dt = real_dt * sim_speed_multiplier

    while True:
        try:
            # 1. Avanza la simulazione
            await engine.run_tick(sim_dt)

            # 2. Ottieni lo stato aggiornato
            trains_state = await engine.get_all_trains_state()
            
            # 3. Serializza i dati per il JSON
            # (Pydantic v2 usa .model_dump() invece di .dict())
            trains_data = [t.model_dump() for t in trains_state]

            # 4. Invia via WebSocket
            await manager.broadcast_json({"type": "train_update", "trains": trains_data})
            
            # 5. Attendi il prossimo tick
            await asyncio.sleep(real_dt)
            
        except Exception as e:
            print(f"Errore nel loop di simulazione: {e}")
            # Pausa prima di riprovare
            await asyncio.sleep(1)


# --- Eventi di Avvio e Spegnimento ---
@app.on_event("startup")
async def on_startup():
    """
    Carica i dati (qui usiamo dati fittizi) e avvia 
    il motore e il loop di simulazione.
    """
    global engine
    
    # --- Dati Fittizi per la Simulazione ---
    sections = [
        Section(section_id=1),
        Section(section_id=2, is_switch=True), # Scambio
        Section(section_id=3), # Binario A
        Section(section_id=4), # Binario B
        Section(section_id=5), # Sezione comune
    ]
    
    connections = [
        Connection(from_section_id=1, to_section_id=2, is_active=True),
        Connection(from_section_id=2, to_section_id=3, is_active=True), # Default: Binario A
        Connection(from_section_id=2, to_section_id=4, is_active=False), # Alternativa: Binario B
        Connection(from_section_id=3, to_section_id=5, is_active=True), # Merge
        Connection(from_section_id=4, to_section_id=5, is_active=True), # Merge
    ]
    
    train_types = [
        TrainType(train_type_id=1, type_name="Regionale", priority_index=2, cruising_speed=5.0), # 5 sezioni/min
        TrainType(train_type_id=2, type_name="Alta Velocità", priority_index=1, cruising_speed=10.0), # 10 sezioni/min
    ]
    
    trains = [
        Train(train_id=101, train_code="R_101", train_type_id=1, current_section_id=1, status='Moving'),
        Train(train_id=201, train_code="AV_201", train_type_id=2, current_section_id=1, position_offset=0.2, status='Moving'),
    ]
    # --- Fine Dati Fittizi ---
    
    # Inizializza il motore
    engine = SimulationEngine(sections, connections, train_types, trains)
    
    # Avvia il loop di simulazione come task in background
    print("Avvio del loop di simulazione in background...")
    asyncio.create_task(simulation_loop(tick_rate_hz=10, sim_speed_multiplier=5))


# --- Endpoints API REST ---

@app.get("/api/v1/trains", response_model=List[Train], tags=["Treni"])
async def get_all_trains():
    """
    Restituisce una lista di tutti i treni con la loro posizione
    (current_section_id, position_offset) e il loro stato.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non ancora pronto.")
    return await engine.get_all_trains_state()

@app.post("/api/v1/switches/{section_id}/set", tags=["Scambi"])
async def set_switch(section_id: int, payload: SwitchSetPayload):
    """
    Imposta la connessione attiva per lo scambio specificato,
    modificando lo stato all'interno del motore di simulazione.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non ancora pronto.")
        
    try:
        await engine.set_switch_position(section_id, payload.to_section_id)
        return {"status": "ok", "message": f"Scambio {section_id} impostato su {payload.to_section_id}"}
    except ValueError as e:
        # Errore se lo scambio è occupato o la sezione non è valida
        raise HTTPException(status_code=400, detail=str(e))


# --- Endpoint WebSocket ---

@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket che invia lo stato di tutti i treni
    ad ogni tick di simulazione.
    """
    await manager.connect(websocket)
    try:
        # Invia lo stato attuale non appena connesso
        if engine:
            trains_state = await engine.get_all_trains_state()
            trains_data = [t.model_dump() for t in trains_state]
            await websocket.send_json({"type": "initial_state", "trains": trains_data})

        # Mantieni la connessione aperta
        while True:
            # Aspetta messaggi (anche se non li usiamo)
            await websocket.receive_text()
            
    except WebSocketDisconnect:
        print(f"Client disconnesso: {websocket.client}")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"Errore WebSocket: {e}")
        manager.disconnect(websocket)


# --- Esecuzione (per test) ---
if __name__ == "__main__":
    print("Avvio del server TrenoSim su http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)