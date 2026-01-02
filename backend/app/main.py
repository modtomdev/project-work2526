import asyncio
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
import csv
from io import StringIO
import asyncpg
from typing import List, Optional

from models import Train, Section, Connection, TrainType, RailBlock
from simulation import SimulationEngine

app = FastAPI(title="TrainSim V3", version="3.0")

engine: Optional[SimulationEngine] = None
db_pool: Optional[asyncpg.pool.Pool] = None

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try: await connection.send_json(data)
            except: pass

manager = ConnectionManager()

async def simulation_loop(tick_rate: int = 10):
    real_dt = 1.0 / tick_rate
    while True:
        if engine:
            try:
                await engine.run_tick(real_dt)
                full_trains = await engine.get_full_state()
                await manager.broadcast({"type": "tick", "trains": [t.model_dump() for t in full_trains]})
            except Exception as e:
                print(f"Sim Loop Error: {e}")
        await asyncio.sleep(real_dt)

@app.on_event("startup")
async def startup():
    global engine, db_pool
    DB_DSN = "postgres://myuser:mypassword@db:5432/mydb"
    
    sections, connections, train_types, rail_blocks, stops = [], [], [], [], []
    
    try:
        db_pool = await asyncpg.create_pool(dsn=DB_DSN)
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT section_id FROM sections")
            sections = [Section(section_id=r['section_id']) for r in rows]
            
            rows = await conn.fetch("SELECT from_section_id, to_section_id, is_active FROM section_connections")
            connections = [Connection(**dict(r)) for r in rows]

            rows = await conn.fetch("SELECT * FROM train_types")
            train_types = [TrainType(**dict(r)) for r in rows]

            rows = await conn.fetch("SELECT block_id, block_name, section_id FROM rail_blocks")
            rail_blocks = [RailBlock(**dict(r)) for r in rows]

            # Load Stops
            rows = await conn.fetch("SELECT stop_id, stop_name, section_id FROM stops")
            stops = [dict(r) for r in rows]
            
            print(f"Loaded {len(sections)} sections, {len(stops)} stops.")
    except Exception as e:
        print(f"DB Error: {e}. Starting empty.")

    engine = SimulationEngine(sections, connections, train_types, [], blocks=rail_blocks, stops=stops)
    asyncio.create_task(simulation_loop())

@app.post("/api/v1/load_trains")
async def api_load_trains(file: UploadFile = File(...)):
    """CSV: train_id, train_code, train_type_id, current_section_id, num_wagons, desired_stop"""
    if not engine: raise HTTPException(503, "Engine not ready")
    
    content = await file.read()
    reader = csv.DictReader(StringIO(content.decode('utf-8')))
    
    new_trains = []
    for row in reader:
        # Parse desired_stop (handle empty string or null)
        d_stop = row.get('desired_stop')
        final_stop_id = int(d_stop) if d_stop and d_stop.strip() else None

        new_trains.append(Train(
            train_id=int(row['train_id']),
            train_code=row['train_code'],
            train_type_id=int(row['train_type_id']),
            current_section_id=int(row['current_section_id']),
            num_wagons=int(row.get('num_wagons', 1)),
            desired_stop_id=final_stop_id, # New Field
            status='Moving'
        ))
    
    await engine.add_trains(new_trains)
    return {"added": len(new_trains)}

@app.websocket("/ws/traffic")
async def ws_traffic(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True: await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/ws-debug", response_class=HTMLResponse)
async def get_debug_ui():
    with open('./websocket-debug.html', "r") as text_file:
        websocket_debug_page = text_file.read()
    return websocket_debug_page

@app.get("/api/v1/sections")
async def get_sections(): return await engine.get_sections_state()
@app.get("/api/v1/connections")
async def get_connections(): return await engine.get_connections_state()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)