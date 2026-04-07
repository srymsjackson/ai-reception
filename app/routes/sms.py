"""Simple read-only SMS-related endpoints."""

from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.db import get_session
from app.services.lead_service import list_leads

router = APIRouter(prefix="/sms", tags=["sms"])


@router.get("/leads")
def get_leads(session: Session = Depends(get_session)):
    """Return all captured leads (newest first)."""
    return list_leads(session)