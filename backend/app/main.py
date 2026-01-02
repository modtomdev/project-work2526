import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Optional
from fastapi import UploadFile, File
from fastapi.responses import HTMLResponse
import csv
from io import StringIO

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
            wagons_state = await engine.get_wagons_state()
            
            # 3. Serializza i dati per il JSON
            trains_data = [t.model_dump() for t in trains_state]
            wagons_data = [w.model_dump() for w in wagons_state]

            # 4. Invia via WebSocket
            await manager.broadcast_json({
                "type": "train_update",
                "trains": trains_data,
                "wagons": wagons_data
            })
            
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
    
    # --- Dati Fittizi per la Simulazione (mappa semplice con 2 ingressi e 4 piattaforme centrali) ---
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

        # From merge (5) to center platforms (this section behaves as a switch)
        Connection(from_section_id=5, to_section_id=6, is_active=True),
        Connection(from_section_id=5, to_section_id=7, is_active=False),
        Connection(from_section_id=5, to_section_id=8, is_active=False),
        Connection(from_section_id=5, to_section_id=9, is_active=False),

        # Each center platform goes to right switch
        Connection(from_section_id=6, to_section_id=10, is_active=True),
        Connection(from_section_id=7, to_section_id=10, is_active=True),
        Connection(from_section_id=8, to_section_id=10, is_active=True),
        Connection(from_section_id=9, to_section_id=10, is_active=True),

        # Right side branches
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

    # Inizializza il motore
    engine = SimulationEngine(sections, connections, train_types, trains)
    
    # Avvia il loop di simulazione come task in background
    print("Avvio del loop di simulazione in background...")
    asyncio.create_task(simulation_loop(tick_rate_hz=10, sim_speed_multiplier=5))

    # --- Nuovi Endpoint: Sezioni, Connessioni, Caricamento CSV ---
@app.get("/api/v1/sections", tags=["Network"])
async def api_get_sections():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non pronto")
    return await engine.get_sections_state()


@app.get("/api/v1/connections", tags=["Network"])
async def api_get_connections():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non pronto")
    return await engine.get_connections_state()


@app.get("/api/v1/wagons", tags=["Wagons"])
async def api_get_wagons():
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non pronto")
    return await engine.get_wagons_state()


@app.post("/api/v1/load_trains", tags=["Admin"])
async def api_load_trains(file: UploadFile = File(...)):
    """Carica un CSV con treni e li aggiunge alla simulazione.

    CSV columns expected: train_id,train_code,train_type_id,current_section_id,position_offset,status
    """
    if engine is None:
        raise HTTPException(status_code=503, detail="Simulatore non pronto")

    content = await file.read()
    try:
        text = content.decode('utf-8')
    except Exception:
        raise HTTPException(status_code=400, detail="File non decodificabile come UTF-8")

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
            raise HTTPException(status_code=400, detail=f"Errore riga CSV: {e}")

    await engine.add_trains(new_trains)
    return {"status": "ok", "added": len(new_trains)}

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

html_debug_page = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket Debugger</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <style>
            #log { height: 400px; overflow-y: scroll; background: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-family: monospace; }
            .msg-sent { color: #0d6efd; }
            .msg-received { color: #198754; }
            .msg-error { color: #dc3545; }
        </style>
    </head>
    <body class="container py-5">
        <h2 class="mb-4">🔌 WebSocket Tester</h2>
        
        <div class="row mb-3">
            <div class="col-md-8">
                <div class="input-group">
                    <span class="input-group-text">ws://</span>
                    <input type="text" id="wsUrl" class="form-control" value="">
                    <button class="btn btn-success" onclick="connect()">Connetti</button>
                    <button class="btn btn-danger" onclick="disconnect()">Disconnetti</button>
                </div>
            </div>
            <div class="col-md-4">
                <span id="status" class="badge bg-secondary">Disconnesso</span>
            </div>
        </div>

        <div class="row">
            <div class="col-md-6">
                <h5>Invia Messaggio</h5>
                <form onsubmit="sendMessage(event)">
                    <textarea id="messageText" class="form-control mb-2" rows="3" placeholder='{"action": "hello"}'></textarea>
                    <button class="btn btn-primary w-100">Invia</button>
                </form>
            </div>
            <div class="col-md-6">
                <h5>Log Eventi <button class="btn btn-sm btn-outline-secondary float-end" onclick="clearLog()">Clear</button></h5>
                <div id="log"></div>
            </div>
        </div>

        <script>
            var ws = null;
            // Imposta l'URL di default basandosi sulla finestra del browser (gestisce le porte di Docker automaticamente)
            document.getElementById('wsUrl').value = window.location.host + "/ws";

            function log(msg, type) {
                var logDiv = document.getElementById('log');
                var div = document.createElement('div');
                div.className = type;
                div.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
                logDiv.appendChild(div);
                logDiv.scrollTop = logDiv.scrollHeight;
            }

            function connect() {
                var url = "ws://" + document.getElementById("wsUrl").value;
                ws = new WebSocket(url);
                
                ws.onopen = function() {
                    document.getElementById("status").className = "badge bg-success";
                    document.getElementById("status").textContent = "Connesso";
                    log("Connessione stabilita", "text-dark");
                };
                
                ws.onmessage = function(event) {
                    log("RX: " + event.data, "msg-received");
                };

                ws.onclose = function() {
                    document.getElementById("status").className = "badge bg-danger";
                    document.getElementById("status").textContent = "Disconnesso";
                    log("Connessione chiusa", "msg-error");
                };
            }

            function disconnect() {
                if(ws) ws.close();
            }

            function sendMessage(event) {
                event.preventDefault();
                var input = document.getElementById("messageText");
                if(ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(input.value);
                    log("TX: " + input.value, "msg-sent");
                } else {
                    alert("Non sei connesso!");
                }
            }
            
            function clearLog() {
                document.getElementById('log').innerHTML = '';
            }
        </script>
    </body>
</html>
"""

@app.get("/ws-debug", response_class=HTMLResponse)
async def get_debug_ui():
    return html_debug_page

# --- Esempio di Endpoint WebSocket ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo dal container Docker: {data}")

# --- Esecuzione (per test) ---
if __name__ == "__main__":
    print("Avvio del server TrenoSim su http://0.0.0.0:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)