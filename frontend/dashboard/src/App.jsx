import React, { useMemo, useState, useEffect, useRef } from "react";

// --- CONFIGURATION ---
const API_URL = "http://localhost:8000/api/network";
const UPLOAD_URL = "http://localhost:8000/api/v1/load_trains";
const CLEAR_URL = "http://localhost:8000/api/v1/trains";
const WS_URL = "ws://localhost:8000/ws/traffic"; 
const GRID_SIZE = 40;
const TRACK_WIDTH = 6;
const HIT_AREA_WIDTH = 40;

// --- GEOMETRIC MAPPING ---
const ROW_CONFIG = [
  { id: "row-0", y: 0, xOffset: 0, startId: 0, endId: 41 },
  { id: "row-1", y: 1, xOffset: 0, startId: 100, endId: 141 },
  { id: "row-2", y: 2, xOffset: 9, startId: 200, endId: 224 },
  { id: "row-3", y: 3, xOffset: 19, startId: 300, endId: 310 },
];

const DIAGONAL_CHAINS = [
  [1000, 1001, 2, "end", 105, "start"],
  [1010, 1011, 10, "end", 113, "start"],
  [1020, 1021, 18, "end", 121, "start"],
  [1030, 1031, 33, "start", 130, "end"],
  [1040, 1041, 41, "start", 138, "end"],
  [2000, 2001, 106, "end", 200, "start"],
  [2010, 2011, 110, "end", 204, "start"],
  [2020, 2021, 118, "end", 212, "start"],
  [2030, 2031, 136, "start", 224, "end"],
  [3010, 3011, 208, "end", 300, "start"],
  [3020, 3021, 224, "start", 310, "end"],
  [3000, 3001, 200, "end", "SPUR_RIGHT", "none"],
];

// [NEW] Arrow Configuration
const DIRECTION_ARROWS = [
  { sectionId: 0, direction: "right" },
  { sectionId: 41, direction: "right" },
  { sectionId: 100, direction: "left" },
  { sectionId: 141, direction: "left" },
];

const stringToColor = (str) => {
  if (!str) return "#ddd";
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 70%, 45%)`;
};

const TrainMapLive = () => {
  // --- STATE ---
  const [sectionMap, setSectionMap] = useState(new Map());
  const [stopList, setStopList] = useState([]); 
  const [loading, setLoading] = useState(true);
  const [hoveredBlock, setHoveredBlock] = useState(null);
  const [activeTrains, setActiveTrains] = useState([]); 
  const [wsStatus, setWsStatus] = useState("DISCONNECTED");
  
  // File Upload State
  const fileInputRef = useRef(null);
  const [uploadStatus, setUploadStatus] = useState("");

  // --- 1. FETCH STATIC TOPOLOGY ---
  useEffect(() => {
    fetch(API_URL)
      .then((res) => res.json())
      .then((data) => {
        const map = new Map();
        data.sections.forEach((sec) => map.set(sec.section_id, sec.block_name));
        setSectionMap(map);
        setStopList(data.stops || []);
        setLoading(false);
      })
      .catch((err) => console.error("API Error:", err));
  }, []);

  // --- 2. WEBSOCKET CONNECTION ---
  useEffect(() => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log("Connected to Traffic Stream");
      setWsStatus("CONNECTED");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "tick") {
          setActiveTrains(data.trains);
        }
      } catch (e) {
        console.error("WS Parse Error", e);
      }
    };

    ws.onclose = () => setWsStatus("DISCONNECTED");
    ws.onerror = (err) => {
      console.error("WS Error", err);
      setWsStatus("ERROR");
    };

    return () => ws.close();
  }, []);

  // --- 3. HANDLERS ---
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setUploadStatus("Uploading...");

    try {
      const response = await fetch(UPLOAD_URL, {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        const result = await response.json();
        setUploadStatus(`Success: Added ${result.added} trains`);
        if (fileInputRef.current) fileInputRef.current.value = "";
      } else {
        setUploadStatus("Upload Failed");
      }
    } catch (error) {
      console.error("Upload Error:", error);
      setUploadStatus("Error uploading file");
    }
    setTimeout(() => setUploadStatus(""), 3000);
  };

  const handleClearTrains = async () => {
    if (!window.confirm("Are you sure you want to remove ALL trains?")) return;
    
    try {
      const response = await fetch(CLEAR_URL, { method: "DELETE" });
      if (response.ok) {
        setUploadStatus("All trains cleared");
        setActiveTrains([]); 
      } else {
        setUploadStatus("Failed to clear trains");
      }
    } catch (error) {
      console.error("Clear Error:", error);
      setUploadStatus("Error clearing trains");
    }
    setTimeout(() => setUploadStatus(""), 3000);
  };

  // --- 4. BUILD VISUAL SEGMENTS ---
  const segments = useMemo(() => {
    const segs = [];
    const nodeMap = new Map();
    const addNode = (key, x, y) =>
      nodeMap.set(key, { x: x * GRID_SIZE + 50, y: y * GRID_SIZE + 50 });

    ROW_CONFIG.forEach((row) => {
      for (let i = row.startId; i <= row.endId; i++) {
        const xStart = row.xOffset + (i - row.startId);
        addNode(`${i}_start`, xStart, row.y);
        addNode(`${i}_end`, xStart + 1, row.y);
        segs.push({
          id: i,
          block: sectionMap.get(i) || "UNKNOWN",
          type: "horizontal",
          x1: xStart * GRID_SIZE + 50,
          y1: row.y * GRID_SIZE + 50,
          x2: (xStart + 1) * GRID_SIZE + 50,
          y2: row.y * GRID_SIZE + 50,
        });
      }
    });

    DIAGONAL_CHAINS.forEach(([seg1, seg2, fromId, fromAnchor, toId, toAnchor]) => {
      const startPt = nodeMap.get(`${fromId}_${fromAnchor}`);
      let endPt = null;

      if (toId === "SPUR_LEFT") {
        endPt = { x: startPt.x - GRID_SIZE * 0.8, y: startPt.y + GRID_SIZE * 0.8 };
      } else if (toId === "SPUR_RIGHT") {
        endPt = { x: startPt.x + GRID_SIZE * 0.8, y: startPt.y + GRID_SIZE * 0.8 };
      } else {
        endPt = nodeMap.get(`${toId}_${toAnchor}`);
      }

      if (startPt && endPt) {
        const midX = (startPt.x + endPt.x) / 2;
        const midY = (startPt.y + endPt.y) / 2;
        segs.push({
          id: seg1, block: sectionMap.get(seg1) || "UNKNOWN", type: "diag",
          x1: startPt.x, y1: startPt.y, x2: midX, y2: midY,
        });
        segs.push({
          id: seg2, block: sectionMap.get(seg2) || "UNKNOWN", type: "diag",
          x1: midX, y1: midY, x2: endPt.x, y2: endPt.y,
        });
      }
    });
    return segs;
  }, [sectionMap]);

  if (loading) return <div className="p-10">Loading Topology...</div>;

  return (
    <div className="p-5 bg-slate-50 min-h-screen font-sans">
      {/* HEADER */}
      <div className="mb-4 p-4 bg-white rounded shadow-sm border flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Live Traffic Control</h2>
          <div className="flex gap-4 text-sm mt-1 items-center">
            <span className={`font-bold ${wsStatus === "CONNECTED" ? "text-green-600" : "text-red-500"}`}>
              ● {wsStatus}
            </span>
            <span className="text-slate-500">Active Trains: {activeTrains.length}</span>
            
            <div className="flex items-center gap-2 ml-4 border-l pl-4">
              <input 
                type="file" 
                accept=".csv" 
                ref={fileInputRef}
                onChange={handleFileUpload}
                className="hidden" 
              />
              <button 
                onClick={() => fileInputRef.current?.click()}
                className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
              >
                Load CSV
              </button>
              <button 
                onClick={handleClearTrains}
                className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded font-medium transition-colors"
              >
                Clear Trains
              </button>
              {uploadStatus && (
                <span className={`text-sm ${uploadStatus.includes("Error") || uploadStatus.includes("Failed") ? "text-red-600" : "text-green-600"}`}>
                  {uploadStatus}
                </span>
              )}
            </div>
          </div>
        </div>
        
        {hoveredBlock && (
          <div className="px-4 py-2 rounded bg-gray-800 text-white font-mono shadow-md">
            BLOCK: {hoveredBlock}
          </div>
        )}
      </div>

      {/* MAP CONTAINER */}
      <div className="overflow-auto border border-slate-300 bg-white shadow-inner relative rounded-lg" style={{ height: "600px" }}>
        <svg width="2200" height="500" className="mt-10 ml-10">
          <g>
            {/* 1. DRAW TRACKS */}
            {segments.map((seg) => {
              const isHovered = hoveredBlock === seg.block;
              const baseColor = stringToColor(seg.block);
              const opacity = isHovered ? 1 : 0.3; 
              const strokeWidth = isHovered ? TRACK_WIDTH + 2 : TRACK_WIDTH;
              const cx = (seg.x1 + seg.x2) / 2;
              const cy = (seg.y1 + seg.y2) / 2;

              return (
                <g
                  key={seg.id}
                  onMouseEnter={() => setHoveredBlock(seg.block)}
                  onMouseLeave={() => setHoveredBlock(null)}
                  className="cursor-pointer"
                  style={{ pointerEvents: "all" }}
                >
                  <line x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2} stroke="transparent" strokeWidth={HIT_AREA_WIDTH} />
                  <line 
                    x1={seg.x1} y1={seg.y1} x2={seg.x2} y2={seg.y2} 
                    stroke={baseColor} strokeOpacity={opacity} strokeWidth={strokeWidth} strokeLinecap="round" 
                    className="pointer-events-none" 
                  />
                  <text
                    x={cx} y={cy - 12} textAnchor="middle" 
                    fill={isHovered ? "#000" : "#cbd5e1"} fontSize="9" fontFamily="monospace"
                    className="select-none pointer-events-none"
                  >
                    {seg.id}
                  </text>
                </g>
              );
            })}

             {/* 2. DRAW DIRECTION ARROWS [NEW] */}
            {DIRECTION_ARROWS.map((arrow, idx) => {
              const seg = segments.find((s) => s.id === arrow.sectionId);
              if (!seg) return null;

              const cx = (seg.x1 + seg.x2) / 2;
              const cy = (seg.y1 + seg.y2) / 2;
              const yOffset = -25; // How high above the track

              return (
                <g key={`arrow-${idx}`} transform={`translate(${cx}, ${cy + yOffset})`}>
                  {arrow.direction === "right" ? (
                    <path
                      d="M -10 0 L 10 0 M 5 -5 L 10 0 L 5 5"
                      stroke="#64748b"
                      strokeWidth="2"
                      fill="none"
                    />
                  ) : (
                    <path
                      d="M 10 0 L -10 0 M -5 -5 L -10 0 L -5 5"
                      stroke="#64748b"
                      strokeWidth="2"
                      fill="none"
                    />
                  )}
                </g>
              );
            })}

            {/* 3. DRAW STOPS */}
            {stopList.map((stop) => {
              const seg = segments.find(s => s.id === stop.section_id);
              if (!seg) return null;
              
              const cx = (seg.x1 + seg.x2) / 2;
              const cy = (seg.y1 + seg.y2) / 2;

              return (
                <g key={stop.stop_id} transform={`translate(${cx}, ${cy})`}>
                  {/* Flag Pole */}
                  <line x1="0" y1="0" x2="0" y2="-15" stroke="#333" strokeWidth="2" />
                  {/* Flag Banner */}
                  <path d="M0,-15 L12,-10 L0,-5 Z" fill="#ef4444" stroke="#7f1d1d" strokeWidth="1" />
                  {/* Stop Label */}
                  <text x="0" y="-18" textAnchor="middle" fontSize="8" fill="#555" fontWeight="bold">
                    {stop.stop_name || stop.stop_id}
                  </text>
                  <circle r="5" fill="transparent"
                     onMouseEnter={() => setHoveredBlock(`STOP: ${stop.stop_name}`)}
                     onMouseLeave={() => setHoveredBlock(null)}
                  />
                </g>
              );
            })}

            {/* 4. DRAW TRAINS */}
            {activeTrains.map((train) => (
              <g key={train.train_id}>
                {train.wagons.map((wagon) => {
                  if (wagon.section_id === null) return null;

                  const seg = segments.find((s) => s.id === wagon.section_id);
                  if (!seg) return null; 

                  const x = seg.x1 + (seg.x2 - seg.x1) * wagon.position_offset;
                  const y = seg.y1 + (seg.y2 - seg.y1) * wagon.position_offset;
                  const angle = Math.atan2(seg.y2 - seg.y1, seg.x2 - seg.x1) * (180 / Math.PI);
                  
                  const isLoco = wagon.wagon_index === 0;
                  const color = isLoco ? "#dc2626" : "#f59e0b"; 
                  const width = isLoco ? 32 : 28;
                  const height = 14;

                  return (
                    <g 
                      key={wagon.wagon_id} 
                      transform={`translate(${x}, ${y}) rotate(${angle})`}
                      className="transition-transform duration-100 ease-linear"
                    >
                      <rect
                        x={-width / 2}
                        y={-height / 2}
                        width={width}
                        height={height}
                        fill={color}
                        stroke="black"
                        strokeWidth="1"
                        rx={isLoco ? 4 : 2}
                      />
                      {isLoco && (
                        <text
                          x="0" y="4"
                          textAnchor="middle"
                          fontSize="9"
                          fontWeight="bold"
                          fill="white"
                          style={{ pointerEvents: 'none' }}
                        >
                          {train.train_id}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            ))}
          </g>
        </svg>
      </div>
    </div>
  );
};

export default TrainMapLive;