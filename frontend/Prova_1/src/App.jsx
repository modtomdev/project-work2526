import React, { useEffect, useState, useRef, useMemo } from 'react';
import { Train, Activity, Zap, Wifi, WifiOff, Map as MapIcon, PlayCircle, PauseCircle } from 'lucide-react';
import './style.css'

const WS_URL = 'ws://localhost:8000/ws/traffic';
const API_BASE = 'http://localhost:8000/api/v1';

// --- Configurazioni Visualizzazione ---
const SCALE = 80; // Fattore di scala come nel tuo codice originale
const OFFSET_X = 60;
const OFFSET_Y = 60;

// Funzione di utilità per calcolare la posizione a schermo
function scalePos(s) {
  const x = Number(s.x);
  const y = Number(s.y);
  
  // Fallback se le coordinate non sono valide
  if (isNaN(x) || isNaN(y)) {
    return { left: (s.section_id * 30) + OFFSET_X, top: OFFSET_Y };
  }
  return { left: (x * SCALE) + OFFSET_X, top: (y * SCALE) + OFFSET_Y };
}

// --- GENERATORE DATI MOCK (SIMULAZIONE API) ---
// Questa sezione crea dati finti strutturati esattamente come quelli che arriverebbero dall'API

const generateMockData = () => {
  // 1. Simuliamo le Sezioni (Track Layout)
  // Creiamo un semplice circuito ovale
  const sections = [];
  const coords = [
    {x: 0, y: 0}, {x: 1, y: 0}, {x: 2, y: 0}, {x: 3, y: 0}, // Top
    {x: 4, y: 1}, {x: 4, y: 2}, // Right
    {x: 3, y: 3}, {x: 2, y: 3}, {x: 1, y: 3}, {x: 0, y: 3}, // Bottom
    {x: -1, y: 2}, {x: -1, y: 1} // Left
  ];

  coords.forEach((c, idx) => {
    sections.push({
      section_id: idx + 1, // ID numerici come nel tuo esempio
      x: c.x + 2, // Offset per centrare
      y: c.y + 1,
      is_switch: false, // Semplificazione
      is_occupied: false
    });
  });

  // 2. Simuliamo le Connessioni (Linee tra le sezioni)
  const connections = sections.map((s, i) => {
    const nextIndex = (i + 1) % sections.length;
    return {
      source: s.section_id,
      target: sections[nextIndex].section_id
    };
  });

  return { sections, connections };
};

export default function App() {
  // Stato applicazione
  const [useDemo, setUseDemo] = useState(true); // Attivo di default per farti vedere subito i dati
  const [wsStatus, setWsStatus] = useState('disconnected');
  
  const [sections, setSections] = useState([]);
  const [connections, setConnections] = useState([]);
  const [trains, setTrains] = useState([]);
  const [wagons, setWagons] = useState([]);
  
  const wsRef = useRef(null);
  const simulationInterval = useRef(null);

  // --- LOGICA 1: Recupero Dati Reali (API + WS) ---
  useEffect(() => {
    if (useDemo) return;

    // Reset dati
    setWsStatus('connecting');

    // Fetch REST API simulata dalla logica di errore
    fetch(`${API_BASE}/sections`)
      .then(r => r.json())
      .then(setSections)
      .catch(() => console.log("Backend non trovato, passa a Demo per vedere i dati."));
      
    fetch(`${API_BASE}/connections`)
      .then(r => r.json())
      .then(setConnections)
      .catch(() => {});

    const ws = new WebSocket(WS_URL);
    ws.onopen = () => setWsStatus('connected');
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'initial_state' || msg.type === 'train_update') {
          setTrains(msg.trains || []);
          setWagons(msg.wagons || []);
        }
      } catch(e) { console.warn(e); }
    };
    ws.onclose = () => setWsStatus('disconnected');
    
    wsRef.current = ws;
    return () => ws.close();
  }, [useDemo]);

  // --- LOGICA 2: Simulazione Dati (Mock Mode) ---
  useEffect(() => {
    if (!useDemo) {
      clearInterval(simulationInterval.current);
      return;
    }

    setWsStatus('demo');
    const { sections: mockSections, connections: mockConnections } = generateMockData();
    setSections(mockSections);
    setConnections(mockConnections);

    // Stato locale per la simulazione del movimento
    let simTrains = [
      { id: 'T1', code: 'FRECCIA-99', secIndex: 0, color: '#ef4444' },
      { id: 'T2', code: 'REG-2045', secIndex: 6, color: '#3b82f6' }
    ];

    // Funzione che aggiorna la posizione dei treni ogni secondo
    const tick = () => {
      // Muovi i treni
      simTrains = simTrains.map(t => ({
        ...t,
        secIndex: (t.secIndex + 1) % mockSections.length
      }));

      // Genera gli oggetti "train" e "wagon" come farebbe l'API
      const apiTrains = simTrains.map(t => ({
        train_id: t.id,
        train_code: t.code,
        status: 'MOVING',
        current_section_id: mockSections[t.secIndex].section_id
      }));

      const apiWagons = [];
      simTrains.forEach(t => {
        const secId = mockSections[t.secIndex].section_id;
        // Locomotiva
        apiWagons.push({
          wagon_id: `${t.id}_W0`,
          train_id: t.id,
          wagon_index: 0,
          section_id: secId,
          position_offset: 0,
          color: t.color
        });
        // Carrozza (simuliamo che sia nella sezione precedente o nella stessa con offset)
        const prevSecIndex = (t.secIndex - 1 + mockSections.length) % mockSections.length;
        const prevSecId = mockSections[prevSecIndex].section_id;
        
        apiWagons.push({
          wagon_id: `${t.id}_W1`,
          train_id: t.id,
          wagon_index: 1,
          section_id: prevSecId, 
          position_offset: 0,
          color: t.color
        });
      });

      setTrains(apiTrains);
      setWagons(apiWagons);
      
      // Aggiorna occupazione sezioni
      setSections(prev => prev.map(s => ({
        ...s,
        is_occupied: apiTrains.some(t => t.current_section_id === s.section_id)
      })));
    };

    tick(); // Primo tick immediato
    simulationInterval.current = setInterval(tick, 1000); // Aggiorna ogni secondo

    return () => clearInterval(simulationInterval.current);
  }, [useDemo]);


  // --- Render ---

  // Disegna le linee di connessione tra le sezioni
  const renderConnections = useMemo(() => {
    return connections.map((conn, i) => {
      const s1 = sections.find(s => s.section_id === conn.source);
      const s2 = sections.find(s => s.section_id === conn.target);
      if (!s1 || !s2) return null;
      const p1 = scalePos(s1);
      const p2 = scalePos(s2);
      return (
        <line 
          key={i} 
          x1={p1.left + 20} y1={p1.top + 20} // +20 per centrare nel div (40px)
          x2={p2.left + 20} y2={p2.top + 20} 
          stroke="#4b5563" strokeWidth="4" 
        />
      );
    });
  }, [sections, connections]);

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans p-6 flex flex-col">
      
      {/* Header */}
      <div className="flex justify-between items-center mb-6 pb-4 border-b border-slate-700">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Train className="text-blue-400" /> TrenoSim Dashboard
          </h2>
          <div className="flex gap-4 text-sm text-slate-400 mt-1">
            <span className="flex items-center gap-1">
              {wsStatus === 'connected' || wsStatus === 'demo' ? <Wifi className="w-4 h-4 text-green-400"/> : <WifiOff className="w-4 h-4 text-red-400"/>}
              {wsStatus === 'demo' ? 'Simulazione Demo' : wsStatus}
            </span>
            <span className="flex items-center gap-1"><Activity className="w-4 h-4"/> Treni: {trains.length}</span>
            <span className="flex items-center gap-1"><Zap className="w-4 h-4"/> Vagoni: {wagons.length}</span>
          </div>
        </div>
        
        <button 
          onClick={() => setUseDemo(!useDemo)}
          className={`px-4 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors ${useDemo ? 'bg-blue-600 hover:bg-blue-500' : 'bg-slate-700 hover:bg-slate-600'}`}
        >
          {useDemo ? <><MapIcon size={18}/> Demo Attiva</> : <><Activity size={18}/> Live Mode</>}
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex gap-6 overflow-hidden">
        
        {/* Canvas Area */}
        <div className="flex-1 bg-slate-800 rounded-xl relative shadow-inner overflow-hidden border border-slate-700">
          <svg className="absolute inset-0 w-full h-full pointer-events-none">
            {renderConnections}
          </svg>
          
          {sections.map(s => {
            const pos = scalePos(s);
            return (
              <div
                key={s.section_id}
                className={`absolute w-10 h-10 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-all duration-300
                  ${s.is_occupied ? 'bg-red-900/50 border-red-500 text-red-200' : 'bg-slate-700 border-slate-600 text-slate-400'}
                `}
                style={{ left: pos.left, top: pos.top }}
              >
                {s.section_id}
              </div>
            );
          })}

          {wagons.map(w => {
            const s = sections.find(sec => sec.section_id === w.section_id);
            if (!s) return null;
            const pos = scalePos(s);
            // Logica offset: se è locomotiva o vagone
            const isLoco = w.wagon_index === 0;
            const bgColor = w.color || (isLoco ? '#fbbf24' : '#60a5fa');
            
            return (
              <div
                key={w.wagon_id}
                className="absolute w-8 h-8 rounded shadow-lg flex items-center justify-center text-[10px] font-bold text-slate-900 transition-all duration-1000 ease-linear z-10"
                style={{
                  left: pos.left + 4 + (w.position_offset || 0) * 10, // Centrato leggermente
                  top: pos.top + 4 - (w.wagon_index * 5), // Leggero stack verticale
                  backgroundColor: bgColor,
                  border: isLoco ? '2px solid white' : 'none',
                  zIndex: isLoco ? 20 : 10
                }}
                title={`Train ${w.train_id} - W${w.wagon_index}`}
              >
                {isLoco ? 'L' : `W${w.wagon_index}`}
              </div>
            );
          })}
        </div>

        {/* Sidebar / Logs */}
        <div className="w-80 flex flex-col gap-4">
          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 flex-1 overflow-auto">
            <h3 className="font-bold text-slate-300 mb-3 flex items-center gap-2"><Activity size={16}/> Treni Attivi</h3>
            <div className="space-y-2">
              {trains.map(t => (
                <div key={t.train_id} className="bg-slate-700/50 p-3 rounded-lg border border-slate-600 text-sm">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-white">{t.train_code}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-green-900 text-green-300">{t.status}</span>
                  </div>
                  <div className="text-slate-400 text-xs">
                    ID: {t.train_id} <br/>
                    Sezione Corrente: <span className="text-blue-300 font-mono">#{t.current_section_id}</span>
                  </div>
                </div>
              ))}
              {trains.length === 0 && <div className="text-slate-500 italic text-sm">Nessun treno in movimento.</div>}
            </div>
          </div>

          <div className="bg-slate-800 p-4 rounded-xl border border-slate-700 h-1/3 overflow-auto">
             <h3 className="font-bold text-slate-300 mb-2 text-sm">Debug Log (Raw JSON)</h3>
             <pre className="text-[10px] text-green-400 font-mono overflow-auto whitespace-pre-wrap">
               {JSON.stringify({ trains: trains.length, wagons: wagons.length, sections: sections.length }, null, 2)}
             </pre>
          </div>
        </div>

      </div>
    </div>
  );
}