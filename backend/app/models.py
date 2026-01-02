from pydantic import BaseModel
from typing import Optional
import datetime

class Section(BaseModel):
    """Represents a single track segment (section)."""
    section_id: intBaseModel
    is_switch: bool = False
    is_occupied: bool = False

class Connection(BaseModel):
    """Directional connection between two sections."""
    from_section_id: int
    to_section_id: int
    is_active: bool = True

class RailBlock(BaseModel):
    """Represents a safety block (grouping of sections)."""
    block_id: int
    block_name: str
    section_id: int

class TrainType(BaseModel):
    """Defines properties of a train type."""
    train_type_id: int
    type_name: str
    priority_index: int
    cruising_speed: float # In section/minute

class Train(BaseModel):
    """Represents a single train in the simulation."""
    train_id: int
    train_code: str
    train_type_id: int
    current_section_id: int
    position_offset: float = 0.0
    #status: str = 'Moving'
    num_wagons: int = 1

class Wagon(BaseModel):
    """Represents a single wagon within a train."""
    wagon_id: int
    train_id: int
    wagon_index: int
    section_id: Optional[int] = None
    position_offset: float = 0.0

class ScheduleEntry(BaseModel):
    """Represents a scheduled stop for a train."""
    stop_id: int
    scheduled_arrival_time: Optional[datetime.datetime] = None
    scheduled_departure_time: Optional[datetime.datetime] = None

class SwitchSetPayload(BaseModel):
    """Payload for the API to set a switch target section."""
    to_section_id: int