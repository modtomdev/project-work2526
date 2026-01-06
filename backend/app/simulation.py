"""
Rail Network Simulation Engine

Implements the complete rail network simulation with proper pathfinding,
train movement, block occupancy, and constraint handling.
"""

import asyncio
from collections import deque
from typing import Dict, List, Optional, Set, Tuple
from heapq import heappush, heappop
from models import Section, Connection, TrainType, Train, Wagon, RailBlock, Stop


class SimulationEngine:
    """
    Manages the simulation of trains on the rail network.
    
    Key responsibilities:
    - Track train positions and movements
    - Enforce block occupancy constraints
    - Implement pathfinding with reversing penalty
    - Handle stop constraints and train stopping
    - Manage spawn/despawn logic
    """
    
    SPAWN_POINTS = {0, 141}  # Left spawn at 0, right spawn at 141
    DESPAWN_POINTS = {100, 41}  # Left despawn at 100, right despawn at 41
    STOP_DURATION = 5.0  # Duration to stop at a station (seconds)
    REVERSE_PENALTY = 10.0  # Penalty multiplier for reverse movement in pathfinding
    
    # Stop approach constraints (section_id, must_approach_from_direction)
    STOP_CONSTRAINTS = {
        31: 'left',      # Track 1: must approach from section 30 (left)
        129: 'left',     # Track 2: must approach from section 128 (left)
        213: 'right',    # Track 3: must approach from section 214 (right)
        301: 'right',    # Track 4: must approach from section 302 (right)
    }
    
    def __init__(
        self,
        sections: List[Section],
        connections: List[Connection],
        train_types: List[TrainType],
        blocks: List[RailBlock],
        stops: List[Stop],
        trains: List[Train] = None,
    ):
        """Initialize the simulation engine with network topology and trains."""
        
        if trains is None:
            trains = []
        
        # Store network topology
        self.sections: Dict[int, Section] = {s.section_id: s for s in sections}
        self.connections: List[Connection] = connections
        self.train_types: Dict[int, TrainType] = {tt.train_type_id: tt for tt in train_types}
        self.blocks: Dict[str, RailBlock] = {b.block_name: b for b in blocks}
        self.stops: Dict[int, Stop] = {s.stop_id: s for s in stops}
        
        # Build mappings
        self.section_to_block: Dict[int, str] = {}
        for block in blocks:
            for section in block.sections:
                self.section_to_block[section.section_id] = block.block_name
        
        self.stop_by_section: Dict[int, Stop] = {s.section_id: s for s in stops}
        
        # Build network graph
        self.network: Dict[int, List[Connection]] = {}
        for conn in connections:
            if conn.from_section_id not in self.network:
                self.network[conn.from_section_id] = []
            self.network[conn.from_section_id].append(conn)
        
        # Train state
        self.trains: Dict[int, Train] = {t.train_id: t for t in trains}
        self.wagons: Dict[int, Wagon] = {}
        self.train_wagons: Dict[int, List[int]] = {}
        
        # History tracks recent sections for each train's wagons
        self.train_history: Dict[int, deque] = {}
        
        # Thread safety
        self.lock = asyncio.Lock()
        
        # Initialize wagons for all trains
        self._initialize_wagons()
        self._update_section_occupancy()
    
    def _initialize_wagons(self):
        """Create wagon objects for all trains based on their num_wagons."""
        wagon_id = 1000
        for train in self.trains.values():
            self._create_train_wagons(train, wagon_id)
            wagon_id += max(1, train.num_wagons)
    
    def _create_train_wagons(self, train: Train, start_wagon_id: int):
        """Create wagon objects for a single train and initialize its history."""
        num_wagons = max(1, train.num_wagons)
        self.train_wagons[train.train_id] = []
        
        # Initialize history queue (stores previous section_id for each wagon position)
        # For a train spawning at a section, wagons start out of frame
        history = deque([None] * num_wagons, maxlen=num_wagons)
        
        self.train_history[train.train_id] = history
        
        # Create wagon objects
        for i in range(num_wagons):
            wagon_id = start_wagon_id + i
            
            if i == 0:
                # Head wagon is at train's current position
                section = train.current_section_id
                offset = train.position_offset
            else:
                # Other wagons start out of frame
                section = None
                offset = 0.0
            
            wagon = Wagon(
                wagon_id=wagon_id,
                train_id=train.train_id,
                wagon_index=i,
                section_id=section,
                position_offset=offset
            )
            
            self.wagons[wagon_id] = wagon
            self.train_wagons[train.train_id].append(wagon_id)
    
    def _get_incoming_connections(self, to_section: int) -> List[int]:
        """Get all sections that have direct connections to the given section."""
        incoming = []
        for conn in self.connections:
            if conn.to_section_id == to_section and conn.is_active:
                incoming.append(conn.from_section_id)
        return incoming
    
    def _get_outgoing_connections(
        self,
        from_section: int,
        exclude_from_block: Optional[str] = None
    ) -> List[Tuple[int, Connection]]:
        """
        Get all valid outgoing connections from a section.
        
        Filters out connections blocked by exclude_previous_block_name constraint.
        Returns list of (to_section_id, connection) tuples.
        """
        valid = []
        
        for conn in self.network.get(from_section, []):
            if not conn.is_active:
                continue
            
            # Check exclude_previous_block constraint
            if exclude_from_block and conn.exclude_previous_block_name == exclude_from_block:
                continue
            
            valid.append((conn.to_section_id, conn))
        
        return valid
    
    def _can_enter_section(
        self,
        section_id: int,
        from_section_id: int,
        train_direction: int
    ) -> bool:
        """
        Check if a train can enter a section from another section.
        
        Enforces stop approach constraints:
        - Track 1 (31): must approach from left (section 30)
        - Track 2 (129): must approach from left (section 128)
        - Track 3 (213): must approach from right (section 214)
        - Track 4 (301): must approach from right (section 302)
        """
        if section_id not in self.STOP_CONSTRAINTS:
            return True
        
        constraint = self.STOP_CONSTRAINTS[section_id]
        
        if constraint == 'left':
            # Must approach from the left (lower section ID)
            return from_section_id < section_id
        elif constraint == 'right':
            # Must approach from the right (higher section ID)
            return from_section_id > section_id
        
        return True
    
    def _bfs_shortest_path(
        self,
        start: int,
        target: int,
        avoid_section: Optional[int] = None,
        exclude_from_block: Optional[str] = None
    ) -> Optional[int]:
        """
        Find shortest path from start to target using BFS.
        
        Returns the first hop (next section to move to), or None if no path exists.
        Avoids a specific section if provided.
        Respects exclude_previous_block constraints.
        """
        if start == target:
            return None
        
        queue = deque([(start, None)])  # (current_section, first_hop)
        visited = {start}
        
        if avoid_section is not None:
            visited.add(avoid_section)
        
        while queue:
            current, first_hop = queue.popleft()
            
            for next_sec, conn in self._get_outgoing_connections(current, exclude_from_block):
                if next_sec in visited:
                    continue
                
                if first_hop is None:
                    first_hop = next_sec
                
                if next_sec == target:
                    return first_hop
                
                visited.add(next_sec)
                queue.append((next_sec, first_hop))
        
        return None
    
    def _dijkstra_with_reversing_penalty(
        self,
        start: int,
        target: int,
        avoid_section: Optional[int] = None,
        exclude_from_block: Optional[str] = None
    ) -> Optional[int]:
        """
        Find path using Dijkstra with reversing penalty.
        
        Penalizes reversing direction to prefer forward movement.
        Returns the first hop to take.
        """
        if start == target:
            return None
        
        # Priority queue: (cost, current_section, first_hop, direction)
        # direction: 1 = forward (higher section ID), -1 = reverse (lower section ID)
        pq = [(0, start, None, 0)]
        visited = set()
        
        while pq:
            cost, current, first_hop, prev_direction = heappop(pq)
            
            if current in visited:
                continue
            visited.add(current)
            
            if current == target:
                return first_hop
            
            for next_sec, conn in self._get_outgoing_connections(current, exclude_from_block):
                if next_sec in visited or next_sec == avoid_section:
                    continue
                
                # Determine direction of this move
                if next_sec > current:
                    direction = 1
                else:
                    direction = -1
                
                # Calculate cost
                base_cost = 1
                
                # Apply reversing penalty
                if prev_direction != 0 and direction != prev_direction:
                    base_cost += self.REVERSE_PENALTY
                
                new_cost = cost + base_cost
                new_first_hop = first_hop if first_hop is not None else next_sec
                
                heappush(pq, (new_cost, next_sec, new_first_hop, direction))
        
        return None
    
    async def add_trains(self, new_trains: List[Train]):
        """Add new trains to the simulation during runtime."""
        async with self.lock:
            wagon_id = 1000
            if self.wagons:
                wagon_id = max(w.wagon_id for w in self.wagons.values()) + 1
            
            for train in new_trains:
                if train.train_id not in self.trains:
                    self.trains[train.train_id] = train
                    self._create_train_wagons(train, wagon_id)
                    wagon_id += max(1, train.num_wagons)
            
            self._update_section_occupancy()
    
    def _update_section_occupancy(self):
        """Update is_occupied flag for all sections based on wagon positions."""
        for section in self.sections.values():
            section.is_occupied = False
        
        for wagon in self.wagons.values():
            if wagon.section_id is not None and wagon.section_id in self.sections:
                self.sections[wagon.section_id].is_occupied = True
    
    def _get_occupied_blocks(self) -> Set[str]:
        """Return set of block names that are currently occupied."""
        occupied = set()
        for wagon in self.wagons.values():
            if wagon.section_id is not None:
                block_name = self.section_to_block.get(wagon.section_id)
                if block_name:
                    occupied.add(block_name)
        return occupied
    
    def _find_next_section(
        self,
        from_section: int,
        train: Train,
        occupied_blocks: Set[str],
        prev_section: Optional[int] = None,
        train_history: Optional[object] = None
    ) -> Optional[int]:
        """
        Determine the next section a train should move to.
        
        Considers:
        1. Train's desired destination (stop or despawn point)
        2. Block occupancy constraints
        3. Stop approach constraints
        4. exclude_previous_block constraints
        """
        
        # Determine target section
        target_section = None
        
        if train.desired_stop_id and train.desired_stop_id in self.stops:
            stop = self.stops[train.desired_stop_id]
            target_section = stop.section_id
            print(f"DEBUG _find_next: Train {train.train_id} has desired_stop_id={train.desired_stop_id}, target={target_section}")
        else:
            # Target despawn point based on current position
            if from_section < 70:
                target_section = 100  # Left despawn
            else:
                target_section = 41  # Right despawn
            print(f"DEBUG _find_next: Train {train.train_id} targeting despawn={target_section}")
        
        # Get current block
        current_block = self.section_to_block.get(from_section)
        
        # Use the stored previous_block_name (where locomotive came from)
        previous_block = train.previous_block_name
        
        print(f"DEBUG _find_next: from_section={from_section}, current_block={current_block}, previous_block={previous_block}")
        
        # Find path to target - exclude the block we came from
        next_hop = self._dijkstra_with_reversing_penalty(
            from_section,
            target_section,
            avoid_section=prev_section,
            exclude_from_block=previous_block
        )
        print(f"DEBUG _find_next: dijkstra returned next_hop={next_hop}")
        
        if next_hop is None:
            # Fallback to any available connection
            print(f"DEBUG _find_next: dijkstra returned None, trying fallback")
            for next_sec, conn in self._get_outgoing_connections(from_section, previous_block):
                if next_sec == prev_section:
                    continue
                next_hop = next_sec
                print(f"DEBUG _find_next: fallback found next_hop={next_hop}")
                break
        
        if next_hop is None:
            print(f"DEBUG _find_next: No next_hop found for train {train.train_id}")
            return None
        
        # Check if next section is blocked (but exclude our own current block)
        next_block = self.section_to_block.get(next_hop)
        print(f"DEBUG _find_next: next_hop={next_hop}, next_block={next_block}")
        if next_block and next_block in occupied_blocks and next_block != current_block:
            print(f"DEBUG _find_next: next_block {next_block} is occupied, rejecting")
            return None
        
        # Check stop approach constraint
        can_enter = self._can_enter_section(next_hop, from_section, 1)
        print(f"DEBUG _find_next: can_enter_section={can_enter}")
        if not can_enter:
            return None
        
        print(f"DEBUG _find_next: returning next_hop={next_hop}")
        return next_hop
    
    def _calculate_train_direction(
        self,
        from_section: int,
        to_section: int
    ) -> int:
        """Determine if train is moving forward (1) or backward (-1)."""
        return 1 if to_section > from_section else -1
    
    async def run_tick(self, dt: float):
        """Execute one simulation tick."""
        async with self.lock:
            occupied_blocks = self._get_occupied_blocks()
            
            for train in list(self.trains.values()):
                # Handle stopping state
                if train.status == 'Stopping':
                    train.wait_elapsed += dt
                    if train.wait_elapsed >= self.STOP_DURATION:
                        train.status = 'Moving'
                        train.desired_stop_id = None
                        train.wait_elapsed = 0.0
                    continue
                
                if train.status != 'Moving':
                    continue
                
                # Get train speed
                train_type = self.train_types.get(train.train_type_id)
                if not train_type:
                    print(f"DEBUG: Train {train.train_id} - No train_type found for type_id {train.train_type_id}")
                    continue
                
                # Calculate movement
                speed_units_per_second = train_type.cruising_speed / 60.0
                move_amount = speed_units_per_second * dt
                print(f"DEBUG: Train {train.train_id} - speed={train_type.cruising_speed}, move_amount={move_amount:.4f}")
                
                # Get wagons
                wagon_ids = self.train_wagons.get(train.train_id, [])
                if not wagon_ids:
                    print(f"DEBUG: Train {train.train_id} - No wagons found! train_wagons keys: {list(self.train_wagons.keys())}")
                    continue
                
                head_wagon = self.wagons[wagon_ids[0]]
                history = self.train_history[train.train_id]
                
                print(f"DEBUG: Train {train.train_id} - head_wagon at section {head_wagon.section_id}, offset={head_wagon.position_offset:.4f}")
                
                # Determine current direction
                prev_section = history[0] if history and len(history) > 0 else None
                current_direction = 1 if prev_section is None or head_wagon.section_id > prev_section else -1
                print(f"DEBUG: Train {train.train_id} - prev_section={prev_section}, current_direction={current_direction}")
                
                # Check if train will cross section boundary
                will_cross = False
                if current_direction == 1 and head_wagon.position_offset + move_amount >= 1.0:
                    will_cross = True
                    print(f"DEBUG: Train {train.train_id} - Will cross (forward)")
                elif current_direction == -1 and head_wagon.position_offset + move_amount <= 0.0:
                    will_cross = True
                    print(f"DEBUG: Train {train.train_id} - Will cross (backward)")
                
                # Lookahead: find next section if crossing
                next_section = None
                if will_cross:
                    next_section = self._find_next_section(
                        head_wagon.section_id,
                        train,
                        occupied_blocks,
                        prev_section
                    )
                    print(f"DEBUG: Train {train.train_id} - Lookahead: next_section={next_section}")
                    
                    if next_section is None:
                        # Can't move forward, stop here
                        print(f"DEBUG: Train {train.train_id} - Can't cross, blocking movement")
                        move_amount = 0
                
                # Apply movement
                if move_amount > 0:
                    print(f"DEBUG: Train {train.train_id} - Applying movement: {move_amount:.4f}")
                    head_wagon.position_offset += current_direction * move_amount
                    head_wagon.position_offset += current_direction * move_amount
                    
                    # Handle boundary crossing
                    if will_cross and next_section:
                        # Update history: push current section back
                        history.appendleft(head_wagon.section_id)
                        
                        # Move head to next section
                        head_wagon.section_id = next_section
                        
                        # Reset position offset at new section boundary
                        new_direction = self._calculate_train_direction(head_wagon.section_id, next_section)
                        head_wagon.position_offset = 0.0 if new_direction == 1 else 1.0
                        current_direction = new_direction
                    elif will_cross:
                        # Clamp position if can't cross
                        if current_direction == 1:
                            head_wagon.position_offset = 0.99
                        else:
                            head_wagon.position_offset = 0.01
                
                # Update other wagons based on history
                for i in range(1, len(wagon_ids)):
                    wagon = self.wagons[wagon_ids[i]]
                    if i - 1 < len(history):
                        wagon.section_id = history[i - 1]
                    else:
                        wagon.section_id = None
                    wagon.position_offset = head_wagon.position_offset
                
                # Update train position
                old_section = train.current_section_id
                train.current_section_id = head_wagon.section_id
                train.position_offset = head_wagon.position_offset
                
                # Track block transitions - update previous_block when entering a new block
                current_block = self.section_to_block.get(train.current_section_id)
                if current_block and current_block != self.section_to_block.get(old_section):
                    # Locomotive moved to a different block
                    train.previous_block_name = self.section_to_block.get(old_section)
                
                # Check if reached destination
                if train.desired_stop_id and train.desired_stop_id in self.stops:
                    stop = self.stops[train.desired_stop_id]
                    if train.current_section_id == stop.section_id:
                        train.status = 'Stopping'
                        train.wait_elapsed = 0.0
                elif train.current_section_id in self.DESPAWN_POINTS:
                    # Train reached despawn point, remove it
                    del self.trains[train.train_id]
                    del self.train_wagons[train.train_id]
                    del self.train_history[train.train_id]
                    for wid in wagon_ids:
                        if wid in self.wagons:
                            del self.wagons[wid]
            
            self._update_section_occupancy()
    
    async def get_full_state(self) -> List[Train]:
        """Return complete state of all trains."""
        async with self.lock:
            result = []
            
            for train in self.trains.values():
                # Create a copy of the train
                train_copy = Train(
                    train_id=train.train_id,
                    train_code=train.train_code,
                    train_type_id=train.train_type_id,
                    current_section_id=train.current_section_id,
                    num_wagons=train.num_wagons,
                    desired_stop_id=train.desired_stop_id,
                    status=train.status,
                    position_offset=train.position_offset,
                    wait_elapsed=train.wait_elapsed
                )
                
                result.append(train_copy)
            
            return result
    
    async def get_trains_with_wagons(self) -> List[dict]:
        """Return complete state of all trains with their wagons as JSON-serializable dicts."""
        async with self.lock:
            result = []
            
            for train in self.trains.values():
                wagon_ids = self.train_wagons.get(train.train_id, [])
                wagons = []
                
                for wid in wagon_ids:
                    if wid in self.wagons:
                        wagon = self.wagons[wid]
                        wagons.append({
                            "wagon_id": wagon.wagon_id,
                            "train_id": wagon.train_id,
                            "wagon_index": wagon.wagon_index,
                            "section_id": wagon.section_id,
                            "position_offset": wagon.position_offset
                        })
                
                train_dict = {
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
                }
                
                result.append(train_dict)
            
            return result
