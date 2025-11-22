# TrenoSim - Educational Train Simulator

A Python backend + React frontend for simulating train movements on a railway network with individual wagon tracking, block signaling, and collision avoidance.

## Overview

This project implements an educational train simulator focused on a single fixed station. Trains enter from left/right, split to alternative platforms via switches, converge into 4 central platforms, and exit. Each train can have up to 15 individual wagons, each rendered on the canvas by section position.

**ITS Academy Alto Adriatico Pordenone** - Project Work 2025-2026
Busetto, Castelletti, Modolo, Speranza, Zermano

## Features

- **Individual Wagon Rendering**: Each train has 1-15 wagons; every wagon is rendered independently with live position updates.
- **Block Signaling**: Uses `section_connections.is_active` to control train routing and prevent collisions via section occupancy.
- **WebSocket Streaming**: Real-time train and wagon state broadcast to all connected clients.
- **REST API**: Query/update network, load trains from CSV, control switches dynamically.
- **In-Memory Engine**: Fast simulation with no database setup required.
- **React Dashboard**: Canvas-based visualization showing sections and individual wagons.

## Quick Start (Local)

### Prerequisites

- **Python** 3.9+ (backend)
- **Node.js** 16+ (frontend, npm)
- **PowerShell** (Windows) or **bash** (Linux/macOS)

### Backend Setup & Run

1. **Install Python dependencies**:
   ```powershell
   cd 'c:\Users\Tommaso\Desktop\project-work2526\backend\app'
   python -m pip install -r requirements.txt
   ```

2. **Start the backend server**:
   ```powershell
   python main.py
   ```
   Or with auto-reload:
   ```powershell
   uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```

   Server will print:
   ```
   Avvio del server TrenoSim su http://127.0.0.1:8000
   ```

3. **Verify backend is running**:
   ```powershell
   curl -s "http://127.0.0.1:8000/api/v1/sections" | ConvertFrom-Json | Select-Object -First 3
   ```

### Frontend Setup & Run

1. **Install npm dependencies**:
   ```powershell
   cd 'c:\Users\Tommaso\Desktop\project-work2526\frontend\dashboard'
   npm install
   ```

2. **Start the dev server**:
   ```powershell
   npm run dev
   ```
   Output will show:
   ```
   VITE v5.x.x  ready in xxx ms

   ➜  Local:   http://localhost:5173/
   ```

3. **Open browser** at `http://localhost:5173/`
   - See canvas with sections (blue boxes) and occupied sections (light red).
   - See individual wagons (small dark bars) moving through sections.
   - See a list of trains below the canvas.

## API Reference

### WebSocket Endpoint

**URL**: `ws://127.0.0.1:8000/ws/traffic`

**Connection Messages**:
```json
{
  "type": "initial_state",
  "trains": [
    {"train_id": 101, "train_code": "R_101", "status": "Moving", "current_section_id": 1, ...}
  ],
  "wagons": [
    {"wagon_id": 1001, "train_id": 101, "wagon_index": 0, "section_id": 1, "position_offset": 0.0}
  ]
}
```

**Update Messages** (every tick):
```json
{
  "type": "train_update",
  "trains": [...],
  "wagons": [...]
}
```

### REST Endpoints

#### Trains (`/api/v1/trains`)
- `GET` - List all trains with current state

#### Wagons (`/api/v1/wagons`)
- `GET` - List all wagons with section and position

#### Network (`/api/v1/sections`, `/api/v1/connections`)
- `GET /api/v1/sections` - All sections with coordinates, occupancy, and switch type
- `GET /api/v1/connections` - All connections with active status

#### Switches (`/api/v1/switches/{section_id}/set`)
- `POST` - Set active connection for a switch
  - Body: `{"to_section_id": <int>}`
  - Example: `POST /api/v1/switches/5/set {"to_section_id": 7}`

#### Admin (`/api/v1/load_trains`)
- `POST` - Upload CSV file with new trains (multipart/form-data)

### CSV Format for Train Loading

**Header**: `train_id,train_code,train_type_id,current_section_id,position_offset,num_wagons,status`

**Example CSV**:
```csv
train_id,train_code,train_type_id,current_section_id,position_offset,num_wagons,status
301,R_301,1,1,0.0,3,Moving
302,AV_302,2,1,0.3,5,Moving
303,R_303,1,13,0.0,2,Scheduled
```

**Test Upload** (PowerShell):
```powershell
# Create test CSV
@"
train_id,train_code,train_type_id,current_section_id,position_offset,num_wagons,status
301,R_301,1,1,0.0,4,Moving
"@ | Out-File -Encoding UTF8 test_trains.csv

# Upload
curl -X POST -F "file=@test_trains.csv" "http://127.0.0.1:8000/api/v1/load_trains"
```

## System Architecture

### Backend (Python + FastAPI)

**Files**:
- `backend/app/main.py` - FastAPI application, WebSocket manager, REST endpoints
- `backend/app/models.py` - Pydantic data models (Section, Train, Wagon, Connection, etc.)
- `backend/app/simulation.py` - SimulationEngine core logic (tick, movement, collision detection)
- `backend/app/requirements.txt` - Python dependencies

**Key Classes**:
- `SimulationEngine` - Main simulation loop manager
  - `run_tick(dt)` - Advance all wagon positions
  - `set_switch_position(section_id, target_id)` - Manage routing
  - `get_wagons_state()` - Expose wagon positions
  - `get_sections_state()` - Expose section occupancy
- `Wagon` - Individual wagon data (section_id, position_offset, train_id, wagon_index)
- `ConnectionManager` - WebSocket broadcast to all clients

### Frontend (React + Vite)

**Files**:
- `frontend/dashboard/src/App.jsx` - Main React component (WebSocket connection, API fetching, rendering)
- `frontend/dashboard/src/styles.css` - Canvas and widget styling
- `frontend/dashboard/src/main.jsx` - React entry point
- `frontend/dashboard/package.json` - Build config and dependencies
- `frontend/dashboard/index.html` - HTML shell

**Rendering Logic**:
- Fetch sections and connections from REST API (once on mount).
- Connect to WebSocket and listen for train/wagon updates.
- For each wagon: find its section's coordinates, offset wagons by position_offset, render as small colored bar.
- Locomotive (wagon_index=0) is darker; cars (1+) are lighter.

### Default Network Layout

```
Left Input (1)
    ↓ (Connection active)
Left Switch (2, is_switch=true)
    ├→ Left Platform A (3)
    └→ Left Platform B (4)
        ↓ (Connections active)
Merge Switch (5, is_switch=true)
    ├→ Center Platform 1 (6)
    ├→ Center Platform 2 (7)
    ├→ Center Platform 3 (8)
    └→ Center Platform 4 (9)
        ↓ (All connections active)
Right Switch (10, is_switch=true)
    ├→ Right Platform A (11)
    └→ Right Platform B (12)
        ↓ (Connections active)
Right Output (13)
```

- **Sections 1-4**: Left side (entry, switch, 2 platforms)
- **Sections 5-10**: Central distribution (merge switch → 4 platforms → right switch)
- **Sections 10-13**: Right side (switch, 2 platforms, exit)

**One-way constraint**:
- Left Input (1) → Left Switch (2) has only one outgoing (active).
- Right Switch (10) → Right Output (13) has only one outgoing (active).
- Left Switch and Right Switch are manually controlled via `/api/v1/switches/{id}/set`.

## Collision & Signaling

### Block Signaling Algorithm

1. **Occupancy Check**: Each section tracks `is_occupied` based on whether any wagon occupies it.
2. **Active Routing**: Each section can have multiple outgoing connections; only those with `is_active=True` are traversable.
3. **Movement Step**:
   - Advance each wagon's `position_offset` by `speed_per_second * dt`.
   - When `position_offset >= 1.0`, check if the next section (via active connection) is occupied.
   - If occupied → wagon stops (prevents collision).
   - If free → wagon moves to next section, `position_offset` wraps to remainder.
4. **Switch Control**: Use `POST /api/v1/switches/{section_id}/set` to activate a different outgoing connection only when the switch section is **not occupied** (no wagon currently in it).

### Wagon Movement Order

- Wagons in a train are moved in **reverse order** (tail to head) to simulate realistic train dynamics (rear wagons follow the locomotive).
- Each wagon independently checks occupancy and stops if blocked.

## Configuration & Tuning

### Simulation Speed

In `main.py:simulation_loop()`:
```python
asyncio.create_task(simulation_loop(tick_rate_hz=10, sim_speed_multiplier=5))
```
- `tick_rate_hz=10`: 10 real-time ticks per second.
- `sim_speed_multiplier=5`: Simulated time runs 5x faster (1 second real = 5 seconds simulated).

### Train Types

In `main.py:on_startup()`:
```python
train_types = [
    TrainType(train_type_id=1, type_name="Regionale", priority_index=2, cruising_speed=5.0),
    TrainType(train_type_id=2, type_name="Alta Velocità", priority_index=1, cruising_speed=10.0),
]
```
- `cruising_speed` is in **sections per minute**. Divide by 60 for sections per second.

### Initial Trains

In `main.py:on_startup()`, add trains to the `trains` list:
```python
trains = [
    Train(train_id=101, train_code="R_101", train_type_id=1, current_section_id=1, num_wagons=3, status='Moving'),
    Train(train_id=201, train_code="AV_201", train_type_id=2, current_section_id=1, position_offset=0.2, num_wagons=5, status='Moving'),
]
```

## Docker Deployment

### Backend (Python FastAPI)

```powershell
cd backend/app
docker build -t trenosim-backend .
docker run -p 8000:8000 trenosim-backend
```

### Frontend (React + Vite)

```powershell
cd frontend/dashboard
docker build -t trenosim-frontend .
docker run -p 5173:5173 trenosim-frontend
```

### Docker Compose

Use the provided `compose.dev.yaml`:

```powershell
cd 'c:\Users\Tommaso\Desktop\project-work2526'
docker-compose -f compose.dev.yaml up
```

Both services will start:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

## Troubleshooting

### Backend Issues

**Port 8000 Already in Use**:
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Module Not Found (e.g., `fastapi`)**:
```powershell
python -m pip install fastapi uvicorn pydantic python-multipart
```

**WebSocket Connection Fails in Frontend**:
- Ensure backend is running.
- Check browser console for errors.
- Verify backend is accessible at `http://127.0.0.1:8000/docs` (FastAPI Swagger).

### Frontend Issues

**npm ERR! Cannot find module**:
```powershell
cd frontend/dashboard
rm -r node_modules package-lock.json
npm install
```

**VITE Port 5173 Already in Use**:
```powershell
npm run dev -- --port 5174
```

**Blank Canvas / No Wagons Showing**:
- Open browser DevTools → Console → check for fetch/WebSocket errors.
- Verify `/api/v1/sections` and `/api/v1/wagons` return data.
- Check WebSocket is connected at `ws://localhost:8000/ws/traffic`.

### Network / Simulation Issues

**Trains Don't Move**:
- Check `/api/v1/trains` → status should be `"Moving"`.
- Check `/api/v1/connections` → ensure path exists from train's current section to exit.

**Switch Cannot Be Changed**:
- Ensure the switch section (e.g., section 5) is not occupied.
- Use `GET /api/v1/sections` to verify `is_occupied=false` for the switch.

**Wagons Collide**:
- This indicates a bug in the occupancy logic (shouldn't happen in normal operation).
- Check simulation logs for any errors.
- Reduce `sim_speed_multiplier` to slow down and inspect.

## Future Enhancements

1. **Persistent Database**: Replace in-memory structures with PostgreSQL (use existing `backend/db/init.sql` schema).
2. **Schedule Management**: Implement train schedules and timetable adherence.
3. **Advanced Routing**: Priority-based routing, dynamic speed adjustment, block reservation.
4. **UI Controls**: Dashboard buttons to spawn trains, control switches, pause/resume simulation.
5. **Real-time Stats**: Display delays, throughput, collision events.
6. **Multi-Station**: Expand to multiple fixed stations with inter-station routes.

## License

See `LICENSE` file.

---

**Project Work 2025-2026**
ITS Academy Alto Adriatico Pordenone
