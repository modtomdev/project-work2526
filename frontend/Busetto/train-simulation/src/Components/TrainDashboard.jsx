import './trainDashboard.css'
import React, { useState, useEffect, useRef } from 'react';

// --- CONFIGURAZIONE COLORI ---
const TRAIN_COLORS = {
  moving: '#3b82f6', // Blu
  stopped: '#ef4444', // Rosso
  delayed: '#eab308', // Giallo
};

// --- COMPONENTI GRAFICI STATICI (Per disegnare la mappa) ---
const BinarioVisuale = () => (
  <g stroke="black" strokeWidth="4" fill="none">
    {/* --- 1. LE TRE LINEE PARALLELE --- */}
    {/* Linea Alta (Y=50) */}
    <line x1="0" y1="50" x2="800" y2="50" />
    {/* Linea Media (Y=100) */}
    <line x1="0" y1="100" x2="800" y2="100" />
    {/* Linea Bassa (Y=150) */}
    <line x1="0" y1="150" x2="800" y2="150" />

    {/* --- 2. GLI SCAMBI (Sinistra) --- */}
    {/* Da Alta a Media */}
    <line x1="100" y1="50" x2="150" y2="100" />
    {/* Da Media a Bassa */}
    <line x1="200" y1="100" x2="250" y2="150" />
    {/* Da Bassa a Diagonale (Diramazione) */}
    <line x1="300" y1="150" x2="400" y2="250" />

    {/* --- 3. GLI SCAMBI (Destra - Ritorno) --- */}
    {/* Da Bassa a Media */}
    <line x1="500" y1="150" x2="550" y2="100" />
    {/* Da Media a Alta */}
    <line x1="600" y1="100" x2="650" y2="50" />

    {/* --- 4. DETTAGLI ESTETICI (I pallini blu sui giunti) --- */}
    <g fill="#2563eb" stroke="none">
       {[0, 100, 200, 300, 400, 500, 600, 700, 800].map(x => (
         <React.Fragment key={x}>
           <circle cx={x} cy={50} r="4" />
           <circle cx={x} cy={100} r="4" />
           <circle cx={x} cy={150} r="4" />
         </React.Fragment>
       ))}
       {/* Pallino fine diramazione */}
       <circle cx={400} cy={250} r="4" />
    </g>
  </g>
);

const TrainDashboard = () => {
  // Riferimenti ai vari PERCORSI POSSIBILI (Routes)
  const routeRefs = useRef({});
  
  // Stato dei treni
  // Aggiungiamo 'routeId' per dire al treno quale binario seguire
  const [trains, setTrains] = useState([
    { id: 'FR-9600', progress: 10, speed: 0.3, status: 'moving', routeId: 'main_top' },     // Corre sulla linea alta
    { id: 'REG-2450', progress: 40, speed: 0.2, status: 'moving', routeId: 'main_mid' },    // Corre sulla linea media
    { id: 'IC-500',   progress: 5,  speed: 0.25, status: 'moving', routeId: 'branch_out' }, // Fa gli scambi ed esce in basso
    { id: 'MERCI-1',  progress: 80, speed: 0.1, status: 'stopped', routeId: 'zigzag_up' },  // Risale dalla bassa alla alta
  ]);

  // Funzione che calcola X,Y chiedendo al percorso specifico (routeId)
  const getPositionOnTrack = (progress, routeId) => {
    const track = routeRefs.current[routeId]; // Seleziona il binario giusto
    if (!track) return { x: 0, y: 0 };
    
    const trackLength = track.getTotalLength();
    const point = track.getPointAtLength((progress / 100) * trackLength);
    return { x: point.x, y: point.y };
  };

  // --- SIMULATORE BACKEND ---
  useEffect(() => {
    const intervalId = setInterval(() => {
      setTrains((currentTrains) => 
        currentTrains.map((train) => {
          if (train.status === 'stopped') return train;

          let newProgress = train.progress + train.speed;
          if (newProgress >= 100) newProgress = 0;

          return { ...train, progress: newProgress };
        })
      );
    }, 50);

    return () => clearInterval(intervalId);
  }, []);

  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h2>🚄 Monitoraggio Treni - Scalo Ferroviario</h2>
      
      <div style={{ 
        border: '2px solid #ddd', 
        borderRadius: '10px', 
        position: 'relative', 
        height: '350px', 
        backgroundColor: '#fff',
        overflow: 'hidden'
      }}>
        
        <svg width="100%" height="100%" viewBox="0 0 850 300">
          
          {/* 1. LIVELLO SFONDO: Disegno i binari neri (Statico) */}
          <BinarioVisuale />

          {/* 2. LIVELLO LOGICO: Percorsi Invisibili (Ghost Tracks) 
              Questi sono i percorsi che i treni seguono veramente.
              Devono sovrapporsi perfettamente al disegno sopra.
          */}
          <defs>
             {/* Percorso A: Linea Alta dritta */}
             <path ref={el => routeRefs.current['main_top'] = el} id="main_top" d="M 0 50 L 850 50" />
             
             {/* Percorso B: Linea Media dritta */}
             <path ref={el => routeRefs.current['main_mid'] = el} id="main_mid" d="M 0 100 L 850 100" />
             
             {/* Percorso C: Diramazione (Parte alto -> scende -> diagonale) */}
             <path ref={el => routeRefs.current['branch_out'] = el} id="branch_out" 
                   d="M 0 50 L 100 50 L 150 100 L 200 100 L 250 150 L 300 150 L 400 250" />

             {/* Percorso D: Risalita (Parte basso -> sale -> alto) */}
             <path ref={el => routeRefs.current['zigzag_up'] = el} id="zigzag_up" 
                   d="M 0 150 L 500 150 L 550 100 L 600 100 L 650 50 L 850 50" />
          </defs>

          {/* 3. RENDERING DEI TRENI */}
          {trains.map((train) => {
            // Calcola posizione passando anche la rotta!
            const { x, y } = getPositionOnTrack(train.progress, train.routeId);
            
            return (
              <g key={train.id} style={{ transform: `translate(${x}px, ${y}px)`, transition: 'transform 50ms linear' }}>
                <circle r="10" fill={TRAIN_COLORS[train.status]} stroke="#fff" strokeWidth="2" />
                <text y="-15" textAnchor="middle" fontSize="10" fontWeight="bold" fill="#333">
                  {train.id}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Tabella controlli */}
      <div style={{ marginTop: '20px' }}>
        <table style={{ width: '100%', textAlign: 'left', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #eee' }}>
              <th>Treno</th>
              <th>Rotta</th>
              <th>Progresso</th>
              <th>Stato</th>
              <th>Azione</th>
            </tr>
          </thead>
          <tbody>
            {trains.map(train => (
              <tr key={train.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{padding: '10px'}}><b>{train.id}</b></td>
                <td style={{color: '#666', fontSize: '0.9em'}}>{train.routeId}</td>
                <td>
                    <div style={{width: '100px', height: '6px', background: '#eee', borderRadius: '3px'}}>
                        <div style={{width: `${train.progress}%`, height: '100%', background: TRAIN_COLORS[train.status], borderRadius: '3px'}}></div>
                    </div>
                </td>
                <td style={{ color: TRAIN_COLORS[train.status], fontWeight: 'bold' }}>{train.status}</td>
                <td>
                  <button onClick={() => setTrains(prev => prev.map(t => t.id === train.id ? { ...t, status: t.status === 'stopped' ? 'moving' : 'stopped' } : t))}>
                    {train.status === 'stopped' ? 'Start' : 'Stop'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TrainDashboard;