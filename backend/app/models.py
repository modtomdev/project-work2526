from pydantic import BaseModel
from typing import Optional, List
import datetime

class Section(BaseModel):
    section_id: int
    is_occupied: bool = False

class Connection(BaseModel):
    from_section_id: int
    to_section_id: int
    is_active: bool = True

class RailBlock(BaseModel):
    block_id: int
    block_name: str
    section_id: int

class TrainType(BaseModel):
    train_type_id: int
    type_name: str
    priority_index: int
    cruising_speed: float  # In sections/minute

class Wagon(BaseModel):
    """Represents a single wagon. Index 0 is the Locomotive."""
    wagon_id: int
    train_id: int
    wagon_index: int
    section_id: Optional[int] = None
    position_offset: float = 0.0

class Train(BaseModel):
    """Represents the logical train unit."""
    train_id: int
    train_code: str
    train_type_id: int
    current_section_id: int
    position_offset: float = 0.0
    status: str = 'Moving' 
    num_wagons: int = 1
    
    # [NEW] Direction state: 1 (Forward 0->1), -1 (Reverse 1->0)
    direction: int = 1 
    
    desired_stop_id: Optional[int] = None 
    wait_elapsed: float = 0.0 

    wagons: List[Wagon] = []

class ScheduleEntry(BaseModel):
    stop_id: int
    scheduled_arrival_time: Optional[datetime.datetime] = None
    scheduled_departure_time: Optional[datetime.datetime] = None

class NetworkSection(BaseModel):
    section_id: int
    block_name: str = "UNKNOWN"

class NetworkConnection(BaseModel):
    from_id: int
    to_id: int

# [NEW] Stop Model
class NetworkStop(BaseModel):
    stop_id: int
    stop_name: str
    section_id: int

class NetworkResponse(BaseModel):
    sections: List[NetworkSection]
    connections: List[NetworkConnection]
    stops: List[NetworkStop] # [NEW] Added stops list