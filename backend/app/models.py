from pydantic import BaseModel
from typing import Optional
import datetime

class Section(BaseModel):
    """Represents a single track segment (section)."""
    section_id: int
    is_switch: bool = False
    # Runtime state used by the simulation (not persisted)
    is_occupied: bool = False
    # Optional coordinates for frontend rendering
    x: Optional[int] = None
    y: Optional[int] = None

class Connection(BaseModel):
    """Directional connection between two sections."""
    from_section_id: int
    to_section_id: int
    is_active: bool = True # Traccia lo stato dello scambio

class RailBlock(BaseModel):
    """Represents a safety block (grouping of sections)."""
    block_id: int
    block_name: str
    section_id: int # Una sezione appartiene a un blocco

# --- Train and schedule models ---

class TrainType(BaseModel):
    """Defines properties of a train type."""
    train_type_id: int
    type_name: str
    priority_index: int
    cruising_speed: float # In sezioni/minuto

class Train(BaseModel):
    """Represents a single train in the simulation."""
    train_id: int
    train_code: str
    train_type_id: int
    current_section_id: int
    position_offset: float = 0.0 # Posizione all'interno della sezione (0.0 a 1.0)
    position_offset: float = 0.0
    status: str = 'Scheduled'  # e.g. 'Moving', 'Stopped', 'Scheduled'
    num_wagons: int = 1  # number of wagons (1-15)

class Wagon(BaseModel):
    """Represents a single wagon within a train."""
    wagon_id: int  # unique ID across all wagons
    train_id: int
    wagon_index: int  # 0 = primo vagone (locomotiva), 1-14 = vagoni
    section_id: Optional[int] = None  # section where the wagon is located
    position_offset: float = 0.0  # relative position inside the section (0.0-1.0)

class ScheduleEntry(BaseModel):
    """Represents a scheduled stop for a train."""
    stop_id: int # Corrisponde a una station_id o section_id
    scheduled_arrival_time: Optional[datetime.datetime] = None
    scheduled_departure_time: Optional[datetime.datetime] = None

# --- API models ---

class SwitchSetPayload(BaseModel):
    """Payload for the API to set a switch target section."""
    to_section_id: int