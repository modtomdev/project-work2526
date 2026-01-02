import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Optional
from fastapi import UploadFile, File
from fastapi.responses import HTMLResponse
import csv
from io import StringIO
import asyncpg

from models import Train, Section, Connection, TrainType, SwitchSetPayload, RailBlock
from simulation import SimulationEngine

app = FastAPI(
    title="TrainSim - Railway Network Simulator",
    description="API for controlling and monitoring a railway simulation.",
    version="1.0.0"
)

engine: Optional[SimulationEngine] = None
db_pool: Optional[asyncpg.pool.Pool] = None

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
    global db_pool
    # Replace this DSN with your Postgres connection string
    DB_DSN = "<REPLACE_WITH_POSTGRES_DSN>"

    try:
        db_pool = await asyncpg.create_pool(dsn=DB_DSN)
    except Exception as e:
        print(f"Warning: could not connect to DB on startup: {e}. Falling back to empty dataset.")
        db_pool = None
    
    # If we have a DB pool, load sections, connections, train_types, rail_blocks and stops from Postgres.
    sections = []
    connections = []
    train_types = []
    rail_blocks = []
    stops = []

    if db_pool is not None:
        async with db_pool.acquire() as conn:
            # Load connections first (we'll derive switches from counts)
            try:
                rows = await conn.fetch("SELECT from_section_id, to_section_id, is_active FROM section_connections")
                for r in rows:
                    connections.append(Connection(
                        from_section_id=r['from_section_id'],
                        to_section_id=r['to_section_id'],
                        is_active=bool(r['is_active'])
                    ))

                # Load sections
                rows = await conn.fetch("SELECT section_id FROM sections")
                # Determine which sections are switches (multiple outgoing connections)
                out_counts = {}
                for c in connections:
                    out_counts[c.from_section_id] = out_counts.get(c.from_section_id, 0) + 1

                for r in rows:
                    sid = r['section_id']
                    is_switch = out_counts.get(sid, 0) > 1
                    sections.append(Section(section_id=sid, is_switch=is_switch))

                # Load rail blocks
                rows = await conn.fetch("SELECT block_id, block_name, section_id FROM rail_blocks")
                for r in rows:
                    rail_blocks.append(RailBlock(block_id=r['block_id'], block_name=r['block_name'], section_id=r['section_id']))

                # Load train types
                rows = await conn.fetch("SELECT train_type_id, type_name, priority_index, cruising_speed FROM train_types")
                for r in rows:
                    train_types.append(TrainType(
                        train_type_id=r['train_type_id'],
                        type_name=r['type_name'],
                        priority_index=r['priority_index'],
                        cruising_speed=float(r['cruising_speed'])
                    ))

                # Load stops
                rows = await conn.fetch("SELECT stop_id, stop_name, section_id FROM stops")
                for r in rows:
                    stops.append({
                        'stop_id': r['stop_id'],
                        'stop_name': r['stop_name'],
                        'section_id': r['section_id']
                    })

            except Exception as e:
                print(f"DB read error on startup: {e}")
                sections = []
                connections = []
                train_types = []
                rail_blocks = []
                stops = []
    else:
        print("DB pool not available - simulator will start with empty network.")

    # Start with no trains loaded by default
    trains = []

    # Initialize engine
    engine = SimulationEngine(sections, connections, train_types, trains, blocks=rail_blocks)

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

@app.post("/api/v1/load_trains", tags=["CSV Loader"])
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


@app.on_event("shutdown")
async def on_shutdown():
    """Close DB pool on shutdown."""
    global db_pool
    try:
        if db_pool is not None:
            await db_pool.close()
            print("DB pool closed")
    except Exception as e:
        print(f"Error closing DB pool: {e}")

if __name__ == "__main__":
    print("Starting backend on http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)