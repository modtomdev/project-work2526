import React, { useEffect, useState, useRef } from 'react'

const WS_URL = 'ws://localhost:8000/ws/traffic'
const API_BASE = 'http://localhost:8000/api/v1'

function scalePos(s) {
  const factor = 80
  // FIX: Cast to Number explicitly before checking
  const x = Number(s.x)
  const y = Number(s.y)
  
  // Check for NaN (Not a Number) instead of type
  const hasX = !isNaN(x)
  const hasY = !isNaN(y)

  if (!hasX || !hasY) {
    const fallbackLeft = 20 * (s.section_id || 0) + 50
    const fallbackTop = 50
    return { left: fallbackLeft, top: fallbackTop }
  }
  return { left: x * factor + 50, top: y * factor + 50 }
}

export default function App() {
  const [sections, setSections] = useState([])
  const [connections, setConnections] = useState([])
  const [trains, setTrains] = useState([])
  const [wagons, setWagons] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    // fetch layout
    fetch(`${API_BASE}/sections`).then(r => r.json()).then(data => { console.debug('sections loaded', data); setSections(data) }).catch(console.warn)
    fetch(`${API_BASE}/connections`).then(r => r.json()).then(data => { console.debug('connections loaded', data); setConnections(data) }).catch(console.warn)

    // websocket
    const ws = new WebSocket(WS_URL)
    ws.onopen = () => console.log('WS open')
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'initial_state' || msg.type === 'train_update') {
          setTrains(msg.trains || [])
          setWagons(msg.wagons || [])
          console.debug('ws msg', msg.type, { trains: msg.trains && msg.trains.length, wagons: msg.wagons && msg.wagons.length })
        }
      } catch (e) { console.warn(e) }
    }
    ws.onclose = () => console.log('WS closed')
    wsRef.current = ws

    return () => { ws.close() }
  }, [])

  return (
    <div className="app">
      <h2>TrenoSim Dashboard - Wagons</h2>
      <div className="stats">
        <div>Trains: {trains.length}</div>
        <div>Wagons: {wagons.length}</div>
      </div>
      <div className="canvas">
        {sections.map(s => (
          <div
            key={s.section_id}
            className={`section ${s.is_switch ? 'switch' : ''} ${s.is_occupied ? 'occupied' : ''}`}
            style={s.x != null ? scalePos(s) : {left:20* s.section_id, top: 50}}
          >
            <div className="section-id">#{s.section_id}</div>
          </div>
        ))}

        {wagons.map(w => {
          // draw each wagon at its section coords
          const sec = sections.find(s => String(s.section_id) === String(w.section_id))
          if (!sec) {
            console.warn(`Wagon ${w.wagon_id} on unknown section ${w.section_id}`)
            return null
          }
          const pos = (sec && (typeof sec.x === 'number' && typeof sec.y === 'number')) ? scalePos(sec) : { left: 20 * sec.section_id + 50, top: 50 }
          // Space wagons vertically or offset them slightly
          const wagonOffsetPx = (w.position_offset || 0) * 30
          const verticalSpacing = w.wagon_index * 6  // small vertical spacing per wagon index
          return (
            <div
              key={w.wagon_id}
              className="wagon"
              style={{
                left: pos.left + wagonOffsetPx,
                top: pos.top + verticalSpacing,
                backgroundColor: w.wagon_index === 0 ? '#1a1a1a' : '#273c75'
              }}
              title={`Wagon ${w.wagon_id} (train ${w.train_id}, idx ${w.wagon_index})`}
            >W{w.wagon_index}</div>
          )
        })}
      </div>

      <div className="legend">
        <div><span className="dot"/> Section</div>
        <div><span className="dot occupied"/> Occupied</div>
        <div><span className="dot switch"/> Switch</div>
        <div><span className="dot wagon-head"/> Locomotive (wagon 0)</div>
        <div><span className="dot wagon-car"/> Car (wagon 1+)</div>
      </div>

      <div className="train-list">
        <h3>Trains</h3>
        {trains.map(t => (
          <div key={t.train_id} className="train-item">
            <strong>{t.train_code}</strong> (id={t.train_id}): {t.status} @ section {t.current_section_id}
          </div>
        ))}
      </div>

      <div className="debug-panel" style={{marginTop:12, padding:8, background:'#fff', border:'1px dashed #ccc'}}>
        <h4>Debug</h4>
        <div>WS state: {wsRef.current ? wsRef.current.readyState : 'no-ws'}</div>
        <div>Sections: {sections.length} | Trains: {trains.length} | Wagons: {wagons.length}</div>
        <details style={{maxHeight:200, overflow:'auto'}}>
          <summary>Raw data</summary>
          <pre style={{whiteSpace:'pre-wrap', fontSize:12}}>{JSON.stringify({sections, trains, wagons}, null, 2)}</pre>
        </details>
      </div>
    </div>
  )
}
