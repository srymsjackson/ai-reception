from pydantic import BaseModel
from typing import Optional


class LeadCreate(BaseModel):
    phone_number: str
    caller_name: Optional[str] = None
    intent: str = "booking"
    service_requested: Optional[str] = None
    preferred_barber: Optional[str] = None
    preferred_time: Optional[str] = None
    notes: Optional[str] = None