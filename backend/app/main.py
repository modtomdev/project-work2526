import asyncio
import uvicorn
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import csv
from io import StringIO
import asyncpg
from typing import List, Optional

from models import (
    Train, Section, Connection, TrainType, RailBlock, 
    NetworkResponse, NetworkSection, NetworkConnection
)
from simulation import SimulationEngine

app = FastAPI(title="TrainSim V3", version="3.0")

# --- ADDED CORS FOR REACT FRONTEND ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with specific frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

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
                # Broadcast tick to connected clients
                await manager.broadcast({"type": "tick", "trains": [t.model_dump() for t in full_trains]})
            except Exception as e:
                print(f"Sim Loop Error: {e}")
        await asyncio.sleep(real_dt)

@app.on_event("startup")
async def startup():
    global engine, db_pool
    # Update credentials as needed
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

            rows = await conn.fetch("SELECT stop_id, stop_name, section_id FROM stops")
            stops = [dict(r) for r in rows]
            
            print(f"Loaded {len(sections)} sections, {len(stops)} stops.")
    except Exception as e:
        print(f"DB Error: {e}. Starting empty.")

    engine = SimulationEngine(sections, connections, train_types, [], blocks=rail_blocks, stops=stops)
    asyncio.create_task(simulation_loop())

@app.on_event("shutdown")
async def shutdown():
    if db_pool:
        await db_pool.close()

# --- NEW ENDPOINT FOR FRONTEND MAPPING ---
@app.get("/api/network", response_model=NetworkResponse)
async def get_network_topology():
    """
    Returns the static network map: sections combined with their block names,
    and all connections. Used by the Frontend to build the SVG map.
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not initialized")

    async with db_pool.acquire() as conn:
        # 1. Fetch Sections Joined with Blocks (Left Join to include sections without blocks)
        rows_sections = await conn.fetch("""
            SELECT s.section_id, COALESCE(b.block_name, 'UNKNOWN') as block_name
            FROM sections s
            LEFT JOIN rail_blocks b ON s.section_id = b.section_id
            ORDER BY s.section_id ASC
        """)

        # 2. Fetch Connections
        rows_conns = await conn.fetch("""
            SELECT from_section_id, to_section_id 
            FROM section_connections
        """)

        return {
            "sections": [
                NetworkSection(section_id=r["section_id"], block_name=r["block_name"]) 
                for r in rows_sections
            ],
            "connections": [
                NetworkConnection(from_id=r["from_section_id"], to_id=r["to_section_id"]) 
                for r in rows_conns
            ]
        }

@app.post("/api/v1/load_trains")
async def api_load_trains(file: UploadFile = File(...)):
    """CSV: train_id, train_code, train_type_id, current_section_id, num_wagons, desired_stop"""
    if not engine: raise HTTPException(503, "Engine not ready")
    
    content = await file.read()
    reader = csv.DictReader(StringIO(content.decode('utf-8')))
    
    new_trains = []
    for row in reader:
        d_stop = row.get('desired_stop')
        final_stop_id = int(d_stop) if d_stop and d_stop.strip() else None

        new_trains.append(Train(
            train_id=int(row['train_id']),
            train_code=row['train_code'],
            train_type_id=int(row['train_type_id']),
            current_section_id=int(row['current_section_id']),
            num_wagons=int(row.get('num_wagons', 1)),
            desired_stop_id=final_stop_id,
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
    try:
        with open('./websocket-debug.html', "r") as text_file:
            return text_file.read()
    except FileNotFoundError:
        return "debug html file not found"

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)