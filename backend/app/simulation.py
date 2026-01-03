import asyncio
from collections import deque
from typing import Dict, List, Optional, Set
from models import (
    Section, Connection, TrainType, Train, Wagon, ScheduleEntry, RailBlock
)

class SimulationEngine:
    def __init__(
        self,
        sections: List[Section],
        connections: List[Connection],
        train_types: List[TrainType],
        trains: List[Train],
        blocks: List[RailBlock] = [],
        stops: List[dict] = [],
        schedules: Dict[int, List[ScheduleEntry]] = {}
    ):
        self.sections: Dict[int, Section] = {s.section_id: s for s in sections}
        self.train_types: Dict[int, TrainType] = {tt.train_type_id: tt for tt in train_types}
        self.trains: Dict[int, Train] = {t.train_id: t for t in trains}
        
        # Maps
        self.section_to_block: Dict[int, int] = {b.section_id: b.block_id for b in blocks}
        self.stop_to_section: Dict[int, int] = {s['stop_id']: s['section_id'] for s in stops}
        
        # Network Graphs
        self.network: Dict[int, List[Connection]] = {} # Forward: From -> To
        self.reverse_network: Dict[int, List[int]] = {} # Reverse: To -> [From, From]
        
        for conn in connections:
            # Build Forward Graph
            if conn.from_section_id not in self.network:
                self.network[conn.from_section_id] = []
            self.network[conn.from_section_id].append(conn)

            # Build Reverse Graph (For finding tails on spawn)
            if conn.to_section_id not in self.reverse_network:
                self.reverse_network[conn.to_section_id] = []
            self.reverse_network[conn.to_section_id].append(conn.from_section_id)

        self.wagons: Dict[int, Wagon] = {}
        self.train_wagons: Dict[int, List[int]] = {}
        
        # Stores the list of previous sections for every train (The Snake Body)
        # Format: { train_id: deque([sec_minus_1, sec_minus_2, ...]) }
        self.train_history: Dict[int, deque] = {}

        self._initialize_wagons()
        self._update_section_occupancy()
        self.lock = asyncio.Lock()

    def _initialize_wagons(self):
        wagon_id_counter = 1000
        for train in self.trains.values():
            if train.train_id in self.train_wagons: continue
            self._setup_single_train(train, wagon_id_counter)
            wagon_id_counter += getattr(train, 'num_wagons', 1)

    async def add_trains(self, new_trains: List[Train]):
        async with self.lock:
            current_max = 1000
            if self.wagons: current_max = max(w.wagon_id for w in self.wagons.values())
            wagon_id_counter = current_max + 1

            for t in new_trains:
                if t.train_id in self.trains: continue
                self.trains[t.train_id] = t
                self._setup_single_train(t, wagon_id_counter)
                wagon_id_counter += getattr(t, 'num_wagons', 1)
            
            self._update_section_occupancy()

    def _setup_single_train(self, train: Train, start_wagon_id: int):
        """Helper to init wagons and backfill history for the snake tail."""
        self.train_wagons[train.train_id] = []
        count = max(1, getattr(train, 'num_wagons', 1))
        
        # 1. Determine Forward direction (Best Guess)
        next_sec_id = None
        if train.desired_stop_id:
             target_sec = self.stop_to_section.get(train.desired_stop_id)
             if target_sec and target_sec != train.current_section_id:
                 next_sec_id = self._bfs_next_step(train.current_section_id, target_sec)
        
        # 2. Backfill History
        history = deque(maxlen=count)
        curr = train.current_section_id
        
        # 'forbidden_node' tracks the node we just visited to avoid U-turns
        forbidden_node = next_sec_id 
        
        for _ in range(count):
            incoming = self.reverse_network.get(curr, [])
            
            # Filter: Pick a neighbor that is NOT the one we just came from/are going to
            candidates = [x for x in incoming if x != forbidden_node]
            
            if candidates:
                prev = candidates[0] # Pick first valid backward path
                history.append(prev)
                forbidden_node = curr
                curr = prev
            else:
                # Dead end: The rest of the train is "Off Map"
                history.append(None)
                # forbidden_node stays same, curr stays same (doesn't matter)
        
        self.train_history[train.train_id] = history
        
        # 3. Create Wagons
        # Head (Index 0)
        self.wagons[start_wagon_id] = Wagon(
            wagon_id=start_wagon_id, train_id=train.train_id, wagon_index=0,
            section_id=train.current_section_id, position_offset=train.position_offset
        )
        self.train_wagons[train.train_id].append(start_wagon_id)
        
        # Tail (Indices 1..N)
        for i in range(1, count):
            wid = start_wagon_id + i
            # Look up section in history
            hist_sec = history[i-1] if (i-1) < len(history) else None
            
            self.wagons[wid] = Wagon(
                wagon_id=wid, train_id=train.train_id, wagon_index=i,
                section_id=hist_sec, position_offset=train.position_offset
            )
            self.train_wagons[train.train_id].append(wid)

    def _bfs_next_step(self, start_sec: int, target_sec: int) -> Optional[int]:
        if start_sec == target_sec: return None
        queue = deque()
        visited = {start_sec}
        
        neighbors = []
        if start_sec in self.network:
            neighbors = [c.to_section_id for c in self.network[start_sec] if c.is_active]

        for neighbor in neighbors:
            if neighbor == target_sec: return neighbor
            queue.append((neighbor, neighbor)) 
            visited.add(neighbor)

        while queue:
            current, first_step = queue.popleft()
            if current == target_sec: return first_step
            
            curr_neighbors = []
            if current in self.network:
                curr_neighbors = [c.to_section_id for c in self.network[current] if c.is_active]

            for neighbor in curr_neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, first_step))
        return None

    async def run_tick(self, dt: float):
        async with self.lock:
            occupied_blocks = self._get_occupied_blocks()
            STOP_DURATION = 5.0 

            for train in self.trains.values():
                # --- STOPPING LOGIC ---
                if train.status == 'Stopping':
                    train.wait_elapsed += dt
                    if train.wait_elapsed >= STOP_DURATION:
                        train.status = 'Moving'
                        train.desired_stop_id = None
                        train.wait_elapsed = 0.0
                    continue 
                
                if train.status != 'Moving': continue

                train_type = self.train_types.get(train.train_type_id)
                if not train_type: continue

                speed_sps = train_type.cruising_speed / 60.0
                move_dist = speed_sps * dt
                
                wagon_ids = self.train_wagons.get(train.train_id, [])
                if not wagon_ids: continue
                
                head_wagon = self.wagons[wagon_ids[0]]
                history = self.train_history[train.train_id]

                # Identify Target Section
                target_section_id = None
                if train.desired_stop_id:
                    target_section_id = self.stop_to_section.get(train.desired_stop_id)

                # --- HEAD PHYSICS & LOOKAHEAD ---
                next_section = None
                
                if head_wagon.position_offset + move_dist >= 1.0:
                    curr_sec = self.sections.get(head_wagon.section_id)
                    if curr_sec:
                        next_section = self._find_next_active_section(
                            curr_sec.section_id, occupied_blocks, target_section_id
                        )
                        if not next_section or next_section.is_occupied:
                             move_dist = 0.0 # Blocked

                if move_dist <= 0: continue 

                # --- APPLY MOVEMENT (SNAKE LOGIC) ---
                
                # 1. Move Head
                head_wagon.position_offset += move_dist
                
                # 2. Handle Boundary Crossing
                if head_wagon.position_offset >= 1.0:
                    head_wagon.position_offset -= 1.0
                    if next_section:
                        # PUSH old section to History
                        history.appendleft(head_wagon.section_id)
                        # MOVE Head
                        head_wagon.section_id = next_section.section_id
                    else:
                        head_wagon.position_offset = 0.99 # End of line

                # 3. Snap Tail to History
                for i in range(1, len(wagon_ids)):
                    w_id = wagon_ids[i]
                    w = self.wagons[w_id]
                    
                    if (i-1) < len(history):
                        w.section_id = history[i-1]
                    else:
                        w.section_id = None # Should not happen if history len matches wagons
                        
                    w.position_offset = head_wagon.position_offset

                # Sync Train Object
                train.current_section_id = head_wagon.section_id
                train.position_offset = head_wagon.position_offset

                # --- ARRIVAL CHECK ---
                if target_section_id and train.current_section_id == target_section_id:
                     train.status = 'Stopping'
                     train.wait_elapsed = 0.0

            self._update_section_occupancy()

    def _find_next_active_section(self, from_sec: int, occupied_blocks: set, target_sec: Optional[int] = None) -> Optional[Section]:
        conns = self.network.get(from_sec, [])
        if not conns: return None
        
        chosen_conn = None
        
        # Priority 1: Route to Target
        if target_sec:
            next_hop_id = self._bfs_next_step(from_sec, target_sec)
            if next_hop_id:
                for c in conns:
                    if c.to_section_id == next_hop_id and c.is_active:
                        chosen_conn = c
                        break
        
        # Priority 2: Default
        if not chosen_conn:
             for c in conns:
                 if not c.is_active: continue
                 nxt_block = self.section_to_block.get(c.to_section_id)
                 if nxt_block and nxt_block in occupied_blocks: continue
                 return self.sections.get(c.to_section_id)
             return None 

        # Validate Chosen Route
        nxt = self.sections.get(chosen_conn.to_section_id)
        if nxt:
            blk = self.section_to_block.get(nxt.section_id)
            if blk and blk in occupied_blocks: return None 
            return nxt
        return None

    def _get_occupied_blocks(self) -> Set[int]:
        occ = set()
        for w in self.wagons.values():
            if w.section_id is not None: # Skip off-map wagons
                b = self.section_to_block.get(w.section_id)
                if b is not None: occ.add(b)
        return occ

    def _update_section_occupancy(self):
        for s in self.sections.values(): s.is_occupied = False
        for w in self.wagons.values():
            if w.section_id is not None and w.section_id in self.sections:
                self.sections[w.section_id].is_occupied = True

    async def get_full_state(self) -> List[Train]:
        async with self.lock:
            result = []
            for t in self.trains.values():
                t_copy = t.model_copy()
                w_ids = self.train_wagons.get(t.train_id, [])
                t_copy.wagons = [self.wagons[wid].model_copy() for wid in w_ids]
                result.append(t_copy)
            return result
