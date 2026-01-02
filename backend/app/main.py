import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Optional
from fastapi import UploadFile, File
from fastapi.responses import HTMLResponse
import csv
from io import StringIO

from models import Train, Section, Connection, TrainType, SwitchSetPayload
from simulation import SimulationEngine

app = FastAPI(
    title="TrainSim - Railway Network Simulator",
    description="API for controlling and monitoring a railway simulation.",
    version="1.0.0"
)

engine: Optional[SimulationEngine] = None

class ConnectionManager:
    """Manage active WebSocket connections for broadcasting state updates."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        """Sends JSON to all connected devices."""
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

async def simulation_loop(tick_rate_hz: int = 10, sim_speed_multiplier: int = 5):
    """Main loop that advances the simulation engine and broadcasts updates."""
    if engine is None:
        print("Error: engine not initialized.")
        return

    # dt is the actual time interval between ticks
    real_dt = 1.0 / tick_rate_hz
    # sim_dt is the simulated time interval between ticks (can be accelerated)
    sim_dt = real_dt * sim_speed_multiplier

    while True:
        try:
            await engine.run_tick(sim_dt)

            trains_state = await engine.get_all_trains_state()
            wagons_state = await engine.get_wagons_state()
            
            # JSON serialization
            trains_data = [t.model_dump() for t in trains_state]
            wagons_data = [w.model_dump() for w in wagons_state]

            # WS send
            await manager.broadcast_json({
                "type": "train_update",
                "trains": trains_data,
                "wagons": wagons_data
            })
            
            await asyncio.sleep(real_dt)
            
        except Exception as e:
            print(f"Simulation loop error: {e}")
            await asyncio.sleep(1)

@app.on_event("startup")
async def on_startup():
    """Load initial data from DB (mock data here), initialize engine and start simulation loop."""
    global engine
    
    sections = [
        Section(section_id=1, x=0, y=2),  # left_in
        Section(section_id=2, is_switch=True, x=1, y=2),  # left_switch
        Section(section_id=3, x=2, y=1),  # left_platform_A
        Section(section_id=4, x=2, y=3),  # left_platform_B
        Section(section_id=5, is_switch=True, x=3, y=2),  # merge / entry to center (switch)
        Section(section_id=6, x=4, y=0),  # center platform 1
        Section(section_id=7, x=4, y=1),  # center platform 2
        Section(section_id=8, x=4, y=2),  # center platform 3
        Section(section_id=9, x=4, y=3),  # center platform 4
        Section(section_id=10, is_switch=True, x=5, y=2), # right_switch
        Section(section_id=11, x=6, y=1), # right_platform_A
        Section(section_id=12, x=6, y=3), # right_platform_B
        Section(section_id=13, x=7, y=2), # right_out
    ]

    connections = [
        Connection(from_section_id=1, to_section_id=2, is_active=True),
        Connection(from_section_id=2, to_section_id=3, is_active=True),
        Connection(from_section_id=2, to_section_id=4, is_active=False),
        Connection(from_section_id=3, to_section_id=5, is_active=True),
        Connection(from_section_id=4, to_section_id=5, is_active=True),

        Connection(from_section_id=5, to_section_id=6, is_active=True),
        Connection(from_section_id=5, to_section_id=7, is_active=False),
        Connection(from_section_id=5, to_section_id=8, is_active=False),
        Connection(from_section_id=5, to_section_id=9, is_active=False),

        Connection(from_section_id=6, to_section_id=10, is_active=True),
        Connection(from_section_id=7, to_section_id=10, is_active=True),
        Connection(from_section_id=8, to_section_id=10, is_active=True),
        Connection(from_section_id=9, to_section_id=10, is_active=True),

        Connection(from_section_id=10, to_section_id=11, is_active=True),
        Connection(from_section_id=10, to_section_id=12, is_active=False),
        Connection(from_section_id=11, to_section_id=13, is_active=True),
        Connection(from_section_id=12, to_section_id=13, is_active=True),
    ]

    train_types = [
        TrainType(train_type_id=1, type_name="Regionale", priority_index=2, cruising_speed=5.0), # sezioni/min
        TrainType(train_type_id=2, type_name="Alta Velocità", priority_index=1, cruising_speed=10.0),
    ]

    trains = [
        Train(train_id=101, train_code="R_101", train_type_id=1, current_section_id=1, num_wagons=3, status='Moving'),
        Train(train_id=201, train_code="AV_201", train_type_id=2, current_section_id=1, position_offset=0.2, num_wagons=5, status='Moving'),
    ]

    # Initialize engine
    engine = SimulationEngine(sections, connections, train_types, trains)

    # Start simulation loop in background
    print("Starting simulation loop in background...")
    asyncio.create_task(simulation_loop(tick_rate_hz=10, sim_speed_multiplier=5))

@app.get("/api/v1/sections", tags=["Network"])
async def api_get_sections():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return await engine.get_sections_state()

@app.get("/api/v1/connections", tags=["Network"])
async def api_get_connections():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return await engine.get_connections_state()

@app.get("/api/v1/wagons", tags=["Wagons"])
async def api_get_wagons():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")
    return await engine.get_wagons_state()

@app.post("/api/v1/load_trains", tags=["Admin"])
async def api_load_trains(file: UploadFile = File(...)):
    """Upload a CSV with trains and add them to the simulation.
    Expected CSV columns: train_id,train_code,train_type_id,current_section_id,position_offset,status
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except Exception:
        raise HTTPException(status_code=400, detail="File not decodable as UTF-8")

    reader = csv.DictReader(StringIO(text))
    new_trains = []
    for row in reader:
        try:
            new_trains.append(Train(
                train_id=int(row.get('train_id')),
                train_code=row.get('train_code'),
                train_type_id=int(row.get('train_type_id')),
                current_section_id=int(row.get('current_section_id')) if row.get('current_section_id') else None,
                position_offset=float(row.get('position_offset') or 0.0),
                num_wagons=int(row.get('num_wagons') or 1),
                status=row.get('status') or 'Scheduled'
            ))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"CSV row error: {e}")

    await engine.add_trains(new_trains)
    return {"status": "ok", "added": len(new_trains)}

# --- Endpoints API REST ---

@app.get("/api/v1/trains", response_model=List[Train], tags=["Trains"])
async def get_all_trains():
    """
    Returns a list of all trains with their position (current_section_id, position_offset) and status.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready.")
    return await engine.get_all_trains_state()

@app.post("/api/v1/switches/{section_id}/set", tags=["Switches"])
async def set_switch(section_id: int, payload: SwitchSetPayload):
    """
    Sets the specified rail switch on.
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulator not ready.")
        
    try:
        await engine.set_switch_position(section_id, payload.to_section_id)
        return {"status": "ok", "message": f"Switch {section_id} set to {payload.to_section_id}"}
    except ValueError as e:
        # Throws if switch is occupied or section is not valid
        raise HTTPException(status_code=400, detail=str(e))

# --- Endpoints WebSocket ---

@app.websocket("/ws/traffic")
async def websocket_traffic_endpoint(websocket: WebSocket):
    """
    Sends all train status at every simulation tick.
    """
    await manager.connect(websocket)
    try:
        if engine:
            trains_state = await engine.get_all_trains_state()
            trains_data = [t.model_dump() for t in trains_state]
            await websocket.send_json({"type": "initial_state", "trains": trains_data})

        while True:
            await websocket.receive_text() # not actually in use, send json only
            
    except WebSocketDisconnect:
        print(f"Client disconnected: {websocket.client}")
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/ws-debug", response_class=HTMLResponse)
async def get_debug_ui():
    with open('./websocket-debug.html', "r") as text_file:
        websocket_debug_page = text_file.read()
    return websocket_debug_page

if __name__ == "__main__":
    print("Starting backend on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)