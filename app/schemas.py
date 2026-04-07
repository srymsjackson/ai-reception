"""Request/transfer schemas used between API layer and services."""

from sqlmodel import SQLModel
from typing import Optional


class LeadCreate(SQLModel):
    """Validated payload used to create a new Lead record."""

    business_id: int

    phone_number: str
    caller_name: Optional[str] = None

    intent: Optional[str] = None
    service_requested: Optional[str] = None
    preferred_time: Optional[str] = None
    preferred_barber: Optional[str] = None

    notes: Optional[str] = None