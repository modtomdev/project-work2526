from pydantic import BaseModel, Field
from typing import Optional
import datetime

class Section(BaseModel):
    """Rappresenta un singolo segmento di binario."""
    section_id: int
    is_switch: bool = False
    # Campo di stato per la simulazione, non nel DB originale
    is_occupied: bool = False
    # Coordinate opzionali per il rendering frontend (non persistite nel DB)
    x: Optional[int] = None
    y: Optional[int] = None

class Connection(BaseModel):
    """Rappresenta una connessione direzionale tra due sezioni."""
    from_section_id: int
    to_section_id: int
    is_active: bool = True # Traccia lo stato dello scambio

class RailBlock(BaseModel):
    """Rappresenta un blocco di sicurezza (gruppo di sezioni)."""
    block_id: int
    block_name: str
    section_id: int # Una sezione appartiene a un blocco

# --- Modelli dei Treni e Orari ---

class TrainType(BaseModel):
    """Definisce le proprietà di un tipo di treno."""
    train_type_id: int
    type_name: str
    priority_index: int
    cruising_speed: float # In sezioni/minuto

class Train(BaseModel):
    """Rappresenta un singolo treno nella simulazione."""
    train_id: int
    train_code: str
    train_type_id: int
    current_section_id: int
    position_offset: float = 0.0 # Posizione all'interno della sezione (0.0 a 1.0)
    status: str = 'Scheduled' # Es: 'Moving', 'Stopped', 'Scheduled'
    num_wagons: int = 1  # Numero di vagoni (1-15)

class Wagon(BaseModel):
    """Rappresenta un singolo vagone all'interno di un treno."""
    wagon_id: int  # unique ID across all wagons
    train_id: int
    wagon_index: int  # 0 = primo vagone (locomotiva), 1-14 = vagoni
    section_id: Optional[int] = None  # sezione dove si trova il vagone
    position_offset: float = 0.0  # posizione relativa nella sezione (0.0-1.0)

class ScheduleEntry(BaseModel):
    """Rappresenta una fermata programmata per un treno."""
    stop_id: int # Corrisponde a una station_id o section_id
    scheduled_arrival_time: Optional[datetime.datetime] = None
    scheduled_departure_time: Optional[datetime.datetime] = None

# --- Modelli API ---

class SwitchSetPayload(BaseModel):
    """Payload per l'API di impostazione dello scambio."""
    to_section_id: int