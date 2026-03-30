from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class Lead(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str
    caller_name: Optional[str] = None
    intent: str = "unknown"
    service_requested: Optional[str] = None
    preferred_barber: Optional[str] = None
    preferred_time: Optional[str] = None
    notes: Optional[str] = None
    booking_link_sent: bool = False
    owner_notified: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)