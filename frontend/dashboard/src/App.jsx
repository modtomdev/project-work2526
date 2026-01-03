import React, { useMemo, useState, useEffect } from "react";

// --- CONFIGURATION ---
const API_URL = "http://localhost:8000/api/network";
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
  // Row 0 <-> Row 1
  [1000, 1001, 2, "end", 105, "start"],
  [1010, 1011, 10, "end", 113, "start"],
  [1020, 1021, 18, "end", 121, "start"],
  [1030, 1031, 33, "start", 130, "end"],
  [1040, 1041, 41, "start", 138, "end"],

  // Row 1 <-> Row 2
  [2000, 2001, 106, "end", 200, "start"], // Connects to START of 200
  [2010, 2011, 110, "end", 204, "start"],
  [2020, 2021, 118, "end", 212, "start"],
  [2030, 2031, 136, "start", 224, "end"],

  // Row 2 <-> Row 3
  [3010, 3011, 208, "end", 300, "start"],
  [3020, 3021, 224, "start", 310, "end"],

  // SPUR (Section 3000/3001)
  // FIX: Connects to END of 200, creating separation from 2001 (which is at START)
  [3000, 3001, 200, "end", "SPUR_RIGHT", "none"],
];

const stringToColor = (str) => {
  if (!str) return "#ddd";
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 70%, 45%)`;
};

const TrainMapFastAPI = () => {
  const [sectionMap, setSectionMap] = useState(new Map());
  const [loading, setLoading] = useState(true);

  const [hoveredBlock, setHoveredBlock] = useState(null);
  const [activeWagon, setActiveWagon] = useState({ id: "W1", segmentId: 0 });
  const [isRunning, setIsRunning] = useState(false);

  // 1. FETCH DATA
  useEffect(() => {
    fetch(API_URL)
      .then((res) => res.json())
      .then((data) => {
        const map = new Map();
        data.sections.forEach((sec) => {
          map.set(sec.section_id, sec.block_name);
        });
        setSectionMap(map);
        setLoading(false);
      })
      .catch((err) => console.error("API Error:", err));
  }, []);

  // 2. BUILD VISUALS
  const segments = useMemo(() => {
    const segs = [];
    const nodeMap = new Map();
    const addNode = (key, x, y) =>
      nodeMap.set(key, { x: x * GRID_SIZE + 50, y: y * GRID_SIZE + 50 });

    // A. Horizontal Rows
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

    // B. Diagonals & Spurs
    DIAGONAL_CHAINS.forEach(
      ([seg1, seg2, fromId, fromAnchor, toId, toAnchor]) => {
        const startPt = nodeMap.get(`${fromId}_${fromAnchor}`);
        let endPt = null;

        // Handle SPUR logic
        if (toId === "SPUR_LEFT") {
          endPt = {
            x: startPt.x - GRID_SIZE * 0.8,
            y: startPt.y + GRID_SIZE * 0.8,
          };
        } else if (toId === "SPUR_RIGHT") {
          // NEW: Spur branching to the right/down
          endPt = {
            x: startPt.x + GRID_SIZE * 0.8,
            y: startPt.y + GRID_SIZE * 0.8,
          };
        } else {
          endPt = nodeMap.get(`${toId}_${toAnchor}`);
        }

        if (startPt && endPt) {
          const midX = (startPt.x + endPt.x) / 2;
          const midY = (startPt.y + endPt.y) / 2;

          segs.push({
            id: seg1,
            block: sectionMap.get(seg1) || "UNKNOWN",
            type: "diag",
            x1: startPt.x,
            y1: startPt.y,
            x2: midX,
            y2: midY,
          });
          segs.push({
            id: seg2,
            block: sectionMap.get(seg2) || "UNKNOWN",
            type: "diag",
            x1: midX,
            y1: midY,
            x2: endPt.x,
            y2: endPt.y,
          });
        }
      }
    );
    return segs;
  }, [sectionMap]);

  // 3. SIMULATION LOOP
  useEffect(() => {
    if (!isRunning) return;
    const PATH = [0, 1, 2, 1000, 1001, 105, 106, 2000, 2001, 200, 201, 202];
    let index = 0;
    const interval = setInterval(() => {
      index = (index + 1) % PATH.length;
      setActiveWagon({ id: "W1", segmentId: PATH[index] });
    }, 500);
    return () => clearInterval(interval);
  }, [isRunning]);

  if (loading) return <div className="p-10">Connecting to Network...</div>;

  return (
    <div className="p-5 bg-slate-50 min-h-screen font-sans">
      <div className="mb-4 p-4 bg-white rounded shadow-sm border flex justify-between items-center">
        <div>
          <h2 className="text-xl font-bold text-slate-800">Railway Simulator</h2>
        </div>
        <div className="flex items-center gap-4">
          {hoveredBlock && (
            <div className="px-4 py-2 rounded bg-gray-800 text-white font-mono shadow-md">
              BLOCK: {hoveredBlock}
            </div>
          )}
          <button
            onClick={() => setIsRunning(!isRunning)}
            className={`px-4 py-2 rounded text-white font-bold ${
              isRunning ? "bg-red-500" : "bg-green-600"
            }`}
          >
            {isRunning ? "Stop Sim" : "Start Sim"}
          </button>
        </div>
      </div>

      <div
        className="overflow-auto border border-slate-300 bg-white shadow-inner relative rounded-lg"
        style={{ height: "550px" }}
      >
        <svg width="2200" height="400" className="mt-10 ml-10">
          <g>
            {segments.map((seg) => {
              const isHovered = hoveredBlock === seg.block;
              const baseColor = stringToColor(seg.block);
              const displayColor = baseColor;
              const opacity = isHovered ? 1 : 0.4;
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
                  {/* Hit Area */}
                  <line
                    x1={seg.x1}
                    y1={seg.y1}
                    x2={seg.x2}
                    y2={seg.y2}
                    stroke="transparent"
                    strokeWidth={HIT_AREA_WIDTH}
                  />
                  {/* Visual Line */}
                  <line
                    x1={seg.x1}
                    y1={seg.y1}
                    x2={seg.x2}
                    y2={seg.y2}
                    stroke={displayColor}
                    strokeOpacity={opacity}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    className="pointer-events-none"
                  />
                  {/* Label */}
                  <text
                    x={cx}
                    y={cy - 12}
                    textAnchor="middle"
                    fill={isHovered ? "#000" : "#cbd5e1"}
                    fontSize={isHovered ? "12" : "8"}
                    fontWeight={isHovered ? "bold" : "normal"}
                    fontFamily="monospace"
                    className="select-none transition-all duration-200"
                  >
                    {seg.id}
                  </text>
                  {/* Block Label */}
                  {isHovered && (
                    <text
                      x={cx}
                      y={cy + 15}
                      textAnchor="middle"
                      fill={baseColor}
                      fontSize="10"
                      fontWeight="bold"
                      className="pointer-events-none select-none"
                    >
                      BLK {seg.block}
                    </text>
                  )}
                </g>
              );
            })}

            {/* Wagon Overlay */}
            {(() => {
              const seg = segments.find((s) => s.id === activeWagon.segmentId);
              if (!seg) return null;
              const wx = (seg.x1 + seg.x2) / 2;
              const wy = (seg.y1 + seg.y2) / 2;
              const angle =
                Math.atan2(seg.y2 - seg.y1, seg.x2 - seg.x1) * (180 / Math.PI);
              return (
                <g
                  transform={`translate(${wx}, ${wy}) rotate(${angle})`}
                  className="pointer-events-none transition-all duration-500"
                >
                  <rect
                    x="-14"
                    y="-7"
                    width="28"
                    height="14"
                    fill="#1e293b"
                    stroke="orange"
                    strokeWidth="2"
                    rx="2"
                  />
                  <text
                    x="0"
                    y="4"
                    textAnchor="middle"
                    fontSize="9"
                    fontWeight="bold"
                    fill="orange"
                  >
                    W1
                  </text>
                </g>
              );
            })()}
          </g>
        </svg>
      </div>
    </div>
  );
};

export default TrainMapFastAPI;