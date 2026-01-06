from typing import List, Optional
from dataclasses import dataclass
import datetime

@dataclass
class Section:
    section_id: int
    is_occupied: bool = False

@dataclass
class Connection:
    from_section_id: int
    to_section_id: int
    exclude_previous_block_name: Optional[str] = None
    is_active: bool = True

@dataclass
class RailBlock:
    block_name: str
    sections: List[Section]
    @property
    def is_occupied(self) -> bool:
        return any(section.is_occupied for section in self.sections)

@dataclass
class Stop:
    stop_id: int
    stop_name: str
    section_id: int

@dataclass
class TrainType:
    train_type_id: int
    type_name: str
    priority_index: int
    cruising_speed: float

@dataclass
class Wagon:
    wagon_id: int
    train_id: int
    wagon_index: int
    section_id: Optional[int] = None # if None, the wagon is currently out of frame
    position_offset: float = 0.0

@dataclass
class Train:
    train_id: int
    train_code: str
    train_type_id: int
    current_section_id: int
    num_wagons: int
    desired_stop_id: Optional[int] = None # if None, train targets the despawn point
    status: str = 'Moving' # the train is always moving when spawned
    position_offset: float = 0.0
    wait_elapsed: float = 0.0
    previous_block_name: Optional[str] = None # tracks what block the locomotive came from 

@dataclass
class SectionDTO:
    section_id: int
    block_name: str = "UNKNOWN"

@dataclass
class ConnectionDTO:
    from_id: int
    to_id: int

@dataclass
class StopDTO:
    stop_id: int
    stop_name: str
    section_id: int

@dataclass
class NetworkDTO:
    sections: List[SectionDTO]
    connections: List[ConnectionDTO]
    stops: List[StopDTO]