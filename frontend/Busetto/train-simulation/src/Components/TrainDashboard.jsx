import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Play, Pause, TrainFront, Activity, Plus, 
  Trash2, Gauge, AlertTriangle, Zap, List
} from 'lucide-react';

import './TrainDashboard.css';

// --- CONFIGURAZIONE FISICA ---
const PIXELS_PER_WAGON = 14;   
const SAFE_DISTANCE_PX = 40;   
const SLOW_DISTANCE_PX = 90;   
const SPAWN_RATE = 0.015;       
const MIN_SPAWN_GAP = 160; 

// --- CONFIGURAZIONE VISUALIZZAZIONE ---
const SPEED_MULTIPLIER = 60;   // 1 unit speed = 60 km/h
const METERS_PER_PIXEL = 2.5;  // 1 pixel = 2.5 metri

const TRAIN_TYPES = [
  { type: 'Freccia',     color: '#ef4444', glow: '#f87171', speed: 3.0, maxWagons: 7, priority: 'HIGH' },
  { type: 'Regionale',   color: '#3b82f6', glow: '#60a5fa', speed: 1.8, maxWagons: 4, priority: 'MED' },
  { type: 'Intercity',   color: '#10b981', glow: '#34d399', speed: 2.2, maxWagons: 6, priority: 'MED' },
  { type: 'Cargo Heavy', color: '#a855f7', glow: '#c084fc', speed: 1.2, maxWagons: 10, priority: 'LOW' },
];

const ROUTES = ['main_top', 'main_mid', 'branch_out', 'zigzag_up'];

// --- HELPER GEOMETRICO ---
const calculateTrainPoints = (train, trackPath, totalLength) => {
  if (!trackPath || totalLength === 0) return [];
  const points = [];
  
  const headDist = Math.max(0, Math.min(train.distance, totalLength));
  const headPoint = trackPath.getPointAtLength(headDist);
  const nextP = trackPath.getPointAtLength(Math.min(headDist + 4, totalLength)); 
  const angle = Math.atan2(nextP.y - headPoint.y, nextP.x - headPoint.x) * (180 / Math.PI);
  
  points.push({ x: headPoint.x, y: headPoint.y, angle, isHead: true });

  for (let i = 1; i <= train.wagonCount; i++) {
    const wagonDist = train.distance - (i * PIXELS_PER_WAGON);
    if (wagonDist > 0) {
      const p = trackPath.getPointAtLength(wagonDist);
      const nextWP = trackPath.getPointAtLength(Math.min(wagonDist + 4, totalLength));
      const wAngle = Math.atan2(nextWP.y - p.y, nextWP.x - p.x) * (180 / Math.PI);
      points.push({ x: p.x, y: p.y, angle: wAngle, isHead: false });
    }
  }
  return points;
};

// --- COMPONENTI GRAFICI ---
const Headlight = () => (
  <path d="M 0 0 L 120 -25 L 120 25 Z" fill="url(#headlight-gradient)" fillOpacity="0.4" style={{ mixBlendMode: 'screen' }} />
);

const BinarioVisuale = () => (
  <g className="track-lines pointer-events-none">
    <defs>
      <linearGradient id="headlight-gradient" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stopColor="white" stopOpacity="0.8" />
        <stop offset="100%" stopColor="white" stopOpacity="0" />
      </linearGradient>
      <filter id="glow">
        <feGaussianBlur stdDeviation="2.5" result="coloredBlur"/>
        <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    
    <g stroke="var(--track-color, #334155)" strokeWidth="8" strokeLinecap="round" fill="none" opacity="0.3">
      <line x1="20" y1="50" x2="830" y2="50" />
      <line x1="20" y1="100" x2="830" y2="100" />
      <line x1="20" y1="150" x2="830" y2="150" />
      <path d="M 100 50 L 150 100" />
      <path d="M 200 100 L 250 150" />
      <path d="M 300 150 L 400 250" />
      <path d="M 500 150 L 550 100 L 600 100 L 650 50" />
    </g>

    <g stroke="var(--rail-color, #94a3b8)" strokeWidth="2" strokeLinecap="round" fill="none" opacity="0.6">
       <line x1="20" y1="48" x2="830" y2="48" /> <line x1="20" y1="52" x2="830" y2="52" />
       <line x1="20" y1="98" x2="830" y2="98" /> <line x1="20" y1="102" x2="830" y2="102" />
       <line x1="20" y1="148" x2="830" y2="148" /> <line x1="20" y1="152" x2="830" y2="152" />
       <path d="M 300 148 L 400 248" /> <path d="M 300 152 L 400 252" />
    </g>

    <g fill="#64748b" stroke="none">
       {[50, 250, 450, 650].map(x => (
         <rect key={x} x={x} y={40} width="4" height="20" rx="1" opacity="0.5" />
       ))}
       <text x={400} y={280} textAnchor="middle" className="text-[10px] fill-current font-mono tracking-widest opacity-50">TERMINAL B</text>
    </g>
  </g>
);

const TrainRenderer = ({ train, points, isSelected, onClick }) => {
  if (!points || points.length === 0) return null;

  const head = points[0]; 
  const wagons = points.slice(1);
  const isStopped = train.status === 'stopped' || train.status === 'blocked';
  const color = train.meta.color;

  return (
    <g 
      className="train-group"
      onClick={(e) => { e.stopPropagation(); onClick(train.id); }}
      style={{ opacity: isStopped ? 1 : 0.9 }}
    >
      {wagons.map((w, idx) => (
        <rect
          key={idx}
          x={w.x - 6} y={w.y - 4} width="12" height="8" rx="2"
          fill={color} stroke="rgba(255,255,255,0.5)" strokeWidth="1"
          style={{ 
            transform: `rotate(${w.angle}deg)`, 
            transformOrigin: `${w.x}px ${w.y}px`,
          }}
        />
      ))}

      <g style={{ transform: `translate(${head.x}px, ${head.y}px) rotate(${head.angle}deg)` }}>
        <g transform="translate(10, 0)">
           <Headlight />
        </g>
        
        <path d="M -12 -7 L 10 -7 L 18 0 L 10 7 L -12 7 Z" fill={color} stroke="#fff" strokeWidth="2" filter={isSelected ? "url(#glow)" : ""} />
        <rect x="2" y="-5" width="6" height="10" fill="rgba(0,0,0,0.5)" rx="1" />
      </g>
    </g>
  );
};

// --- COMPONENTE PRINCIPALE ---
const TrainDashboard = () => {
  const routeRefs = useRef({});
  const idCounter = useRef(1);

  const [trains, setTrains] = useState([
    { id: 'T-001', distance: 100, speed: 0, overrideSpeed: null, status: 'moving', routeId: 'main_mid', wagonCount: 6, meta: TRAIN_TYPES[1], totalLength: 0 },
  ]);
  const [visualPoints, setVisualPoints] = useState({});
  const [selectedId, setSelectedId] = useState(null);

  const activeTrainsCount = trains.length;
  const blockedTrainsCount = trains.filter(t => t.status === 'blocked').length;
  
  const avgSpeed = activeTrainsCount > 0 
    ? (trains.reduce((acc, t) => acc + (t.speed * SPEED_MULTIPLIER), 0) / activeTrainsCount).toFixed(0) 
    : 0;

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
  }, []);

  const spawnTrain = () => {
    setTrains(prev => {
      const availableRoutes = ROUTES.filter(route => {
        const trainsOnThisRoute = prev.filter(t => t.routeId === route);
        if (trainsOnThisRoute.length === 0) return true;
        const isBlocked = trainsOnThisRoute.some(t => {
          const trainLen = t.wagonCount * PIXELS_PER_WAGON;
          return (t.distance - trainLen) < MIN_SPAWN_GAP;
        });
        return !isBlocked;
      });

      if (availableRoutes.length === 0) return prev;

      const randomRoute = availableRoutes[Math.floor(Math.random() * availableRoutes.length)];
      const randomType = TRAIN_TYPES[Math.floor(Math.random() * TRAIN_TYPES.length)];
      const wagonNum = Math.floor(Math.random() * (randomType.maxWagons - 3)) + 4;
      
      const pathEl = routeRefs.current[randomRoute];
      const routeLen = pathEl ? pathEl.getTotalLength() : 1000;

      const newTrain = {
        id: `T-${String(idCounter.current++).padStart(3, '0')}`,
        distance: 0,
        speed: 0,
        overrideSpeed: null,
        status: 'moving',
        routeId: randomRoute,
        wagonCount: wagonNum,
        meta: randomType,
        totalLength: routeLen
      };

      setSelectedId(newTrain.id);
      return [...prev, newTrain];
    });
  };

  const removeTrain = (id) => {
    setTrains(prev => prev.filter(t => t.id !== id));
    if (selectedId === id) setSelectedId(null);
  };

  const updateTrainSpeed = (id, newSpeedRatio) => {
    setTrains(prev => prev.map(t => {
      if (t.id !== id) return t;
      return { ...t, overrideSpeed: t.meta.speed * newSpeedRatio };
    }));
  };

  useEffect(() => {
    const intervalId = setInterval(() => {
      setTrains((currentTrains) => {
        const activeTrains = currentTrains.filter(t => {
          const trainLength = t.wagonCount * PIXELS_PER_WAGON;
          return t.distance < (t.totalLength + trainLength + 10);
        });
        
        const trainGeometries = activeTrains.map(t => {
           const path = routeRefs.current[t.routeId];
           if (!path) return { id: t.id, points: [], train: t }; 
           const points = calculateTrainPoints(t, path, t.totalLength);
           return { id: t.id, points, train: t };
        });

        const newVisualMap = {};
        trainGeometries.forEach(g => newVisualMap[g.id] = g.points);
        setVisualPoints(newVisualMap);

        return activeTrains.map((me) => {
          if (me.status === 'stopped') return { ...me, speed: 0 };

          const myGeo = trainGeometries.find(g => g.id === me.id);
          if (!myGeo || myGeo.points.length === 0) return me;

          const myHead = myGeo.points[0];
          let minDist = 10000;

          trainGeometries.forEach(other => {
            if (other.id === me.id) return;
            if (other.points[0] && other.points[0].x < myHead.x - 200) return; 

            other.points.forEach(pt => {
               const dist = Math.sqrt(Math.pow(myHead.x - pt.x, 2) + Math.pow(myHead.y - pt.y, 2));
               if (dist < minDist) {
                 if (me.routeId === other.train.routeId) {
                    if (other.train.distance > me.distance) minDist = dist;
                 } else {
                    minDist = dist;
                 }
               }
            });
          });

          let baseSpeed = me.overrideSpeed !== null ? me.overrideSpeed : me.meta.speed;
          let targetSpeed = baseSpeed;
          let newStatus = me.status;

          if (newStatus === 'blocked') {
            if (minDist < SLOW_DISTANCE_PX) targetSpeed = 0;
            else newStatus = 'moving';
          } else {
            if (minDist < SAFE_DISTANCE_PX) {
               targetSpeed = 0;
               newStatus = 'blocked';
            } else if (minDist < SLOW_DISTANCE_PX) {
               targetSpeed = baseSpeed * 0.3;
            }
          }

          return { 
            ...me, 
            distance: me.distance + targetSpeed, 
            speed: targetSpeed, 
            status: newStatus 
          };
        });
      });

      if (Math.random() < SPAWN_RATE) spawnTrain();

    }, 30); 

    return () => clearInterval(intervalId);
  }, []);

  const toggleManualStop = (id) => {
    setTrains(prev => prev.map(t => 
      t.id === id ? { ...t, status: t.status === 'stopped' ? 'moving' : 'stopped' } : t
    ));
  };

  const selectedTrain = useMemo(() => trains.find(t => t.id === selectedId), [trains, selectedId]);

  return (
    <div className="flex flex-col w-screen h-screen overflow-hidden bg-base-300 font-sans transition-colors duration-500">
      
      {/* HEADER HUD */}
      <div className="flex-none bg-base-100 shadow-md z-20 px-6 py-3 flex items-center justify-between border-b border-base-content/10">
        <div className="flex items-center gap-4">
          <div className="bg-primary text-primary-content p-2 rounded-xl shadow-lg shadow-primary/30">
            <TrainFront size={24} />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">TrainControl <span className="text-primary">OS</span></h1>
            <div className="text-xs opacity-60 font-mono flex gap-3">
               <span>VER 3.1.0</span>
               <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> ONLINE</span>
            </div>
          </div>
        </div>

        <div className="hidden md:flex gap-8 bg-base-200/50 px-6 py-2 rounded-full border border-base-content/5 backdrop-blur-sm">
           <div className="flex flex-col items-center leading-none">
             <span className="text-[10px] uppercase font-bold opacity-50">Active</span>
             <span className="font-mono text-lg font-bold">{activeTrainsCount}</span>
           </div>
           <div className="w-px bg-base-content/20"></div>
           <div className="flex flex-col items-center leading-none">
             <span className="text-[10px] uppercase font-bold opacity-50">Blocked</span>
             <span className={`font-mono text-lg font-bold ${blockedTrainsCount > 0 ? 'text-error' : ''}`}>{blockedTrainsCount}</span>
           </div>
           <div className="w-px bg-base-content/20"></div>
           <div className="flex flex-col items-center leading-none">
             <span className="text-[10px] uppercase font-bold opacity-50">Avg Speed</span>
             <span className="font-mono text-lg font-bold text-secondary">{avgSpeed} <span className="text-[10px]">km/h</span></span>
           </div>
        </div>

        <div className="flex items-center gap-2">
           <button className="btn btn-primary btn-sm gap-2 shadow-lg shadow-primary/20" onClick={spawnTrain}>
             <Plus size={16} /> <span className="hidden sm:inline">Add Train</span>
           </button>
        </div>
      </div>

      {/* MAIN WORKSPACE: MAPPA + SIDEBAR */}
      <div className="flex-1 flex overflow-hidden relative">
        
        {/* RADAR MAP */}
        <div 
          className="flex-1 relative bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 cursor-crosshair mb-32" // Margine inferiore per il pannello
          onClick={() => setSelectedId(null)}
        >
          <div className="absolute inset-0 opacity-10" 
               style={{
                 backgroundImage: `radial-gradient(#fff 1px, transparent 1px)`, 
                 backgroundSize: '30px 30px'
               }}>
          </div>

          <svg width="100%" height="100%" viewBox="0 0 850 350" className="select-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
             <BinarioVisuale />
             <defs>
                <path ref={el => routeRefs.current['main_top'] = el} d="M 0 50 L 850 50" />
                <path ref={el => routeRefs.current['main_mid'] = el} d="M 0 100 L 850 100" />
                <path ref={el => routeRefs.current['branch_out'] = el} d="M 0 50 L 100 50 L 150 100 L 200 100 L 250 150 L 300 150 L 400 250" />
                <path ref={el => routeRefs.current['zigzag_up'] = el} d="M 0 150 L 500 150 L 550 100 L 600 100 L 650 50 L 850 50" />
             </defs>
             {trains.map((train) => (
               <TrainRenderer 
                 key={train.id} 
                 train={train} 
                 points={visualPoints[train.id]} 
                 isSelected={selectedId === train.id}
                 onClick={setSelectedId}
               />
             ))}
          </svg>

          <div className="absolute bottom-4 left-4 text-xs font-mono opacity-30 select-none">
             SECTOR: A-74 // SIGNAL: STRONG
          </div>
        </div>

        {/* SIDEBAR CONTROL PANEL */}
        <div className={`
          absolute right-0 top-0 bottom-32 w-80 bg-base-100/95 backdrop-blur-md shadow-2xl border-l border-base-content/10 transform transition-transform duration-300 z-30
          ${selectedId ? 'translate-x-0' : 'translate-x-full'}
        `}>
           {selectedTrain ? (
             <div className="flex flex-col h-full">
                <div className="p-6 pb-2 relative overflow-hidden">
                   <div className="absolute top-0 right-0 p-4 opacity-10">
                      <TrainFront size={120} strokeWidth={1} />
                   </div>
                   <div className="relative z-10">
                     <div className="flex justify-between items-start">
                        <div className="badge badge-lg font-bold rounded-md mb-2 shadow-lg" style={{backgroundColor: selectedTrain.meta.color, color: '#fff'}}>
                           {selectedTrain.meta.type}
                        </div>
                        <button 
                          className="w-8 h-8 rounded-full bg-red-600 hover:bg-red-700 shadow-lg transition-transform hover:scale-110"
                          onClick={() => setSelectedId(null)}
                          title="Close Panel"
                        >
                        </button>
                     </div>
                     <h2 className="text-3xl font-black tracking-tighter">{selectedTrain.id}</h2>
                     <p className="text-xs opacity-60 font-mono mt-1">ROUTE ID: {selectedTrain.routeId.toUpperCase()}</p>
                   </div>
                </div>

                <div className="divider my-0"></div>

                <div className="p-6 space-y-8 flex-1 overflow-y-auto custom-scrollbar">
                   
                   {/* INFO EXTRA GRID */}
                   <div className="grid grid-cols-2 gap-3">
                      <div className="bg-base-300/50 p-2 rounded border border-base-content/5">
                        <div className="text-[10px] uppercase font-bold opacity-50">Wagons</div>
                        <div className="font-mono text-lg">{selectedTrain.wagonCount}</div>
                      </div>
                      <div className="bg-base-300/50 p-2 rounded border border-base-content/5">
                        <div className="text-[10px] uppercase font-bold opacity-50">Priority</div>
                        <div className="font-mono text-lg text-primary">{selectedTrain.meta.priority}</div>
                      </div>
                   </div>

                   <div className="space-y-4">
                      <div className="flex justify-between items-center">
                        <label className="flex items-center gap-2 font-bold text-sm"><Gauge size={16} className="text-primary"/> LIVE SPEED</label>
                        <span className="font-mono text-xl">
                          {(selectedTrain.speed * SPEED_MULTIPLIER).toFixed(0)} <span className="text-xs opacity-50">km/h</span>
                        </span>
                      </div>
                      <input 
                        type="range" min="0" max="1.5" step="0.1" 
                        className="range range-primary range-xs" 
                        value={selectedTrain.overrideSpeed !== null ? (selectedTrain.overrideSpeed / selectedTrain.meta.speed) : 1}
                        onChange={(e) => updateTrainSpeed(selectedTrain.id, parseFloat(e.target.value))}
                      />
                      <div className="flex justify-between text-[10px] font-mono opacity-50 px-1">
                         <span>STOP</span>
                         <span>NORMAL</span>
                         <span>BOOST</span>
                      </div>
                   </div>

                   <div className="card bg-base-200 p-4 border border-base-content/5">
                      <div className="flex items-center gap-3 mb-3">
                         <div className={`p-2 rounded-lg ${selectedTrain.status === 'blocked' ? 'bg-error text-error-content animate-pulse' : 'bg-success text-success-content'}`}>
                           {selectedTrain.status === 'blocked' ? <AlertTriangle size={20}/> : <Activity size={20}/>}
                         </div>
                         <div>
                            <div className="text-[10px] uppercase font-bold opacity-60">Status</div>
                            <div className="font-bold">{selectedTrain.status.toUpperCase()}</div>
                         </div>
                      </div>
                      <div className="text-xs opacity-70">
                         {selectedTrain.status === 'blocked' 
                           ? "CRITICAL ALERT: Train stopped due to proximity sensor." 
                           : "Systems nominal. Maintaining safe distance."}
                      </div>
                   </div>

                   <div className="grid grid-cols-2 gap-3">
                      <button 
                         className={`btn ${selectedTrain.status === 'stopped' ? 'btn-success' : 'btn-warning'} btn-outline w-full`}
                         onClick={() => toggleManualStop(selectedTrain.id)}
                      >
                         {selectedTrain.status === 'stopped' ? <Play size={18} /> : <Pause size={18} />}
                         {selectedTrain.status === 'stopped' ? "RESUME" : "HALT"}
                      </button>
                      <button 
                         className="btn btn-error btn-outline w-full"
                         onClick={() => removeTrain(selectedTrain.id)}
                      >
                         <Trash2 size={18} /> SCRAP
                      </button>
                   </div>
                </div>

                <div className="p-4 bg-base-200/50 text-[10px] font-mono text-center opacity-50">
                   Distance: {Math.round(selectedTrain.distance * METERS_PER_PIXEL)} / {Math.round(selectedTrain.totalLength * METERS_PER_PIXEL)} m
                </div>
             </div>
           ) : (
             <div className="h-full flex items-center justify-center text-center p-8 opacity-40">
                <div>
                   <Zap size={48} className="mx-auto mb-4"/>
                   <p className="font-bold">NO SIGNAL</p>
                   <p className="text-xs">Select a unit on the radar to establish link.</p>
                </div>
             </div>
           )}
        </div>
      </div>

      {/* BOTTOM PANEL: FLEET OVERVIEW */}
      <div className="h-32 bg-base-100 border-t border-base-content/10 shadow-lg z-40 absolute bottom-0 left-0 right-0 flex flex-col">
        <div className="px-4 py-2 bg-base-200/50 text-xs font-bold uppercase tracking-widest flex items-center gap-2 opacity-70">
           <List size={14}/> Fleet Overview ({activeTrainsCount})
        </div>
        <div className="flex-1 flex items-center gap-4 px-4 overflow-x-auto custom-scrollbar">
           {trains.length === 0 && (
             <div className="w-full text-center text-xs opacity-30 italic">No active units in sector.</div>
           )}
           {trains.map(t => (
             <div 
               key={t.id}
               onClick={() => setSelectedId(t.id)}
               className={`
                 flex-none w-48 bg-base-200 border border-base-content/5 p-3 rounded-xl cursor-pointer transition-all hover:bg-base-300 hover:scale-105 group
                 ${selectedId === t.id ? 'ring-2 ring-primary bg-base-300' : ''}
               `}
             >
               <div className="flex justify-between items-start mb-2">
                 <div className="font-black text-sm">{t.id}</div>
                 <div className={`w-2 h-2 rounded-full ${t.status === 'blocked' ? 'bg-error animate-pulse' : 'bg-success'}`}></div>
               </div>
               <div className="flex justify-between items-end">
                  <div>
                    <div className="text-[10px] opacity-60 uppercase">{t.meta.type}</div>
                    <div className="text-[10px] font-mono opacity-50">{t.wagonCount} wgns</div>
                  </div>
                  <div className="text-lg font-mono leading-none" style={{color: t.meta.color}}>
                     {(t.speed * SPEED_MULTIPLIER).toFixed(0)} <span className="text-[10px] text-base-content opacity-50">km/h</span>
                  </div>
               </div>
             </div>
           ))}
        </div>
      </div>

    </div>
  );
};

export default TrainDashboard;
