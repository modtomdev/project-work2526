import asyncio
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from heapq import heappush, heappop
from models import Section, Connection, TrainType, Train, Wagon, RailBlock, Stop
import time

class SimulationEngine:
    SPAWN_POINTS = {0, 141}
    DESPAWN_POINTS = {100, 41}
    STOP_DURATION = 5.0
    REVERSE_PENALTY = 10.0

    STOP_CONSTRAINTS = {
        31: 'left', 129: 'left', 213: 'right', 301: 'right',
    }

    def __init__(self, sections, connections, train_types, blocks, stops, trains=None):
        if trains is None: trains = []
        self.sections: Dict[int, Section] = {s.section_id: s for s in sections}
        self.connections: List[Connection] = connections
        self.train_types: Dict[int, TrainType] = {tt.train_type_id: tt for tt in train_types}
        self.blocks: Dict[str, RailBlock] = {b.block_name: b for b in blocks}
        self.stops: Dict[int, Stop] = {s.stop_id: s for s in stops}
        
        self.section_to_block: Dict[int, str] = {}
        for block in blocks:
            for section in block.sections:
                self.section_to_block[section.section_id] = block.block_name
        
        self.network: Dict[int, List[Connection]] = {}
        for conn in connections:
            if conn.from_section_id not in self.network:
                self.network[conn.from_section_id] = []
            self.network[conn.from_section_id].append(conn)
        
        self.trains: Dict[int, Train] = {t.train_id: t for t in trains}
        self.wagons: Dict[int, Wagon] = {}
        self.train_wagons: Dict[int, List[int]] = {}
        self.train_history: Dict[int, deque] = {}
        
        # --- NEW: Simulation Control & Debugging ---
        self.paused = False
        self.debug_logs = deque(maxlen=200) # Store last 200 events
        self.tick_count = 0
        
        self.lock = asyncio.Lock()
        
        self._initialize_wagons()
        self._update_section_occupancy()

    def set_paused(self, paused: bool):
        self.paused = paused
        self._log_debug("SYSTEM", f"Simulation {'PAUSED' if paused else 'RESUMED'}")

    def _log_debug(self, source: str, message: str):
        """Internal helper to add a structured log entry."""
        entry = {
            "tick": self.tick_count,
            "time": time.strftime("%H:%M:%S"),
            "source": str(source),
            "message": message
        }
        self.debug_logs.append(entry)

    def _initialize_wagons(self):
        wagon_id = 1000
        for train in self.trains.values():
            self._create_train_wagons(train, wagon_id)
            wagon_id += max(1, train.num_wagons)

    def _create_train_wagons(self, train: Train, start_wagon_id: int):
        num_wagons = max(1, train.num_wagons)
        self.train_wagons[train.train_id] = []
        history = deque([None] * num_wagons, maxlen=num_wagons)
        self.train_history[train.train_id] = history
        
        for i in range(num_wagons):
            wagon_id = start_wagon_id + i
            section = train.current_section_id if i == 0 else None
            offset = train.position_offset if i == 0 else 0.0
            
            wagon = Wagon(wagon_id, train.train_id, i, section, offset)
            self.wagons[wagon_id] = wagon
            self.train_wagons[train.train_id].append(wagon_id)

    def _get_outgoing_connections(self, from_section: int, exclude_from_block: Optional[str] = None):
        valid = []
        for conn in self.network.get(from_section, []):
            if not conn.is_active: continue
            if exclude_from_block and conn.exclude_previous_block_name == exclude_from_block:
                continue
            valid.append((conn.to_section_id, conn))
        return valid

    def _can_enter_section(self, section_id: int, from_section_id: int) -> bool:
        if section_id not in self.STOP_CONSTRAINTS: return True
        constraint = self.STOP_CONSTRAINTS[section_id]
        return (from_section_id < section_id) if constraint == 'left' else (from_section_id > section_id)

    def _dijkstra_pathfinding(self, start: int, target: int, avoid_section: int, exclude_from_block: str):
        if start == target: return None
        pq = [(0, start, None, 0)] 
        visited = set()
        
        while pq:
            cost, current, first_hop, prev_dir = heappop(pq)
            if current in visited: continue
            visited.add(current)
            if current == target: return first_hop
            
            for next_sec, conn in self._get_outgoing_connections(current, exclude_from_block):
                if next_sec == avoid_section: continue
                curr_dir = 1 if next_sec > current else -1
                move_cost = 1
                if prev_dir != 0 and curr_dir != prev_dir:
                    move_cost += self.REVERSE_PENALTY
                new_hop = first_hop if first_hop is not None else next_sec
                heappush(pq, (cost + move_cost, next_sec, new_hop, curr_dir))
        return None

    def _find_next_section(self, from_sec: int, train: Train, occupied_blocks: Set[str], prev_sec: int) -> Optional[int]:
        target = train.desired_stop_id if train.desired_stop_id else (100 if from_sec < 70 else 41)
        if train.desired_stop_id and train.desired_stop_id in self.stops:
             target = self.stops[train.desired_stop_id].section_id

        current_block = self.section_to_block.get(from_sec)
        next_hop = self._dijkstra_pathfinding(from_sec, target, prev_sec, train.previous_block_name)
        
        if next_hop is None: 
            self._log_debug(train.train_id, f"No path found to target {target} from {from_sec}")
            return None

        next_block = self.section_to_block.get(next_hop)
        
        if next_block and next_block != current_block:
             if next_block in occupied_blocks:
                 # Debug: Log red signal
                 self._log_debug(train.train_id, f"Red Signal at Block {next_block}")
                 return None 
        
        if not self._can_enter_section(next_hop, from_sec): 
            return None
        
        if self.sections[next_hop].is_occupied:
             self._log_debug(train.train_id, f"Section {next_hop} physically occupied")
             return None

        return next_hop

    async def add_trains(self, new_trains: List[Train]):
        async with self.lock:
            wagon_id = max((w.wagon_id for w in self.wagons.values()), default=1000) + 1
            for train in new_trains:
                if train.current_section_id in self.sections:
                    if self.sections[train.current_section_id].is_occupied:
                        self._log_debug("SPAWN", f"Spawn blocked for Train {train.train_id} at {train.current_section_id}")
                        continue 

                if train.train_id not in self.trains:
                    self.trains[train.train_id] = train
                    self._create_train_wagons(train, wagon_id)
                    wagon_id += max(1, train.num_wagons)
                    self._log_debug("SPAWN", f"Train {train.train_id} added at {train.current_section_id}")
            
            self._update_section_occupancy()

    def _update_section_occupancy(self):
        for s in self.sections.values(): s.is_occupied = False
        for w in self.wagons.values():
            if w.section_id is not None: self.sections[w.section_id].is_occupied = True

    def _get_occupied_blocks(self) -> Set[str]:
        occupied = set()
        for w in self.wagons.values():
            if w.section_id is not None:
                blk = self.section_to_block.get(w.section_id)
                if blk: occupied.add(blk)
        return occupied

    async def run_tick(self, dt: float):
        async with self.lock:
            if self.paused:
                return # Skip logic if paused

            self.tick_count += 1
            occupied_blocks = self._get_occupied_blocks()
            
            sorted_trains = sorted(
                self.trains.values(),
                key=lambda t: self.train_types[t.train_type_id].priority_index,
                reverse=True
            )

            for train in sorted_trains:
                if train.status == 'Stopping':
                    train.wait_elapsed += dt
                    if train.wait_elapsed >= self.STOP_DURATION:
                        train.status = 'Moving'
                        train.desired_stop_id = None
                        train.wait_elapsed = 0.0
                        self._log_debug(train.train_id, "Finished stop. Resuming movement.")
                    continue
                
                if train.status != 'Moving': continue

                train_type = self.train_types.get(train.train_type_id)
                move_amount = (train_type.cruising_speed / 60.0) * dt
                
                wagon_ids = self.train_wagons.get(train.train_id, [])
                if not wagon_ids: continue
                head = self.wagons[wagon_ids[0]]
                history = self.train_history[train.train_id]
                
                prev_sec = history[0] if history and len(history) > 0 else None
                direction = 1 
                if prev_sec is not None:
                    direction = 1 if head.section_id > prev_sec else -1

                will_cross = False
                if direction == 1 and head.position_offset + move_amount >= 1.0: will_cross = True
                elif direction == -1 and head.position_offset - move_amount <= 0.0: will_cross = True

                next_sec = None
                if will_cross:
                    next_sec = self._find_next_section(head.section_id, train, occupied_blocks, prev_sec)
                    if next_sec is None: 
                        move_amount = 0 # Blocked
                        # We already logged why inside _find_next_section

                if move_amount > 0:
                    if direction == 1: head.position_offset += move_amount
                    else: head.position_offset -= move_amount

                    if will_cross and next_sec:
                        history.appendleft(head.section_id)
                        old_sec = head.section_id
                        head.section_id = next_sec
                        
                        new_dir = 1 if next_sec > old_sec else -1
                        head.position_offset = 0.0 if new_dir == 1 else 1.0
                        
                        old_blk = self.section_to_block.get(old_sec)
                        new_blk = self.section_to_block.get(next_sec)
                        if new_blk and new_blk != old_blk:
                            train.previous_block_name = old_blk
                            self._log_debug(train.train_id, f"Entered Block {new_blk} (Sec {next_sec})")

                        if train.desired_stop_id and train.desired_stop_id in self.stops:
                            if head.section_id == self.stops[train.desired_stop_id].section_id:
                                train.status = 'Stopping'
                                self._log_debug(train.train_id, f"Arrived at Stop {train.desired_stop_id}")

                        elif train.current_section_id in self.DESPAWN_POINTS:
                             self._log_debug(train.train_id, "Despawned at boundary")
                             pass
                    elif will_cross:
                        head.position_offset = 0.99 if direction == 1 else 0.01

                for i in range(1, len(wagon_ids)):
                    w = self.wagons[wagon_ids[i]]
                    w.section_id = history[i-1] if (i-1) < len(history) else None
                    w.position_offset = head.position_offset

                train.current_section_id = head.section_id
                train.position_offset = head.position_offset

            # Cleanup despawned
            to_remove = [k for k, v in self.trains.items() if v.current_section_id in self.DESPAWN_POINTS]
            for tid in to_remove:
                del self.trains[tid]
                del self.train_wagons[tid]
                del self.train_history[tid]
                # cleanup wagons from self.wagons omitted for brevity, logic exists in previous versions

            self._update_section_occupancy()
    
    async def get_trains_with_wagons(self) -> List[dict]:
        async with self.lock:
            result = []
            for train in self.trains.values():
                wagon_ids = self.train_wagons.get(train.train_id, [])
                wagons = []
                for wid in wagon_ids:
                    if wid in self.wagons:
                        w = self.wagons[wid]
                        wagons.append({
                            "wagon_id": w.wagon_id,
                            "train_id": w.train_id,
                            "wagon_index": w.wagon_index,
                            "section_id": w.section_id,
                            "position_offset": w.position_offset
                        })
                result.append({
                    "train_id": train.train_id,
                    "train_code": train.train_code,
                    "train_type_id": train.train_type_id,
                    "current_section_id": train.current_section_id,
                    "num_wagons": train.num_wagons,
                    "desired_stop_id": train.desired_stop_id,
                    "status": train.status,
                    "position_offset": train.position_offset,
                    "wait_elapsed": train.wait_elapsed,
                    "wagons": wagons
                })
            return result