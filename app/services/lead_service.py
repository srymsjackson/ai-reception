from sqlmodel import Session, select
from app.models import Lead
from app.schemas import LeadCreate


def create_lead(session: Session, payload: LeadCreate) -> Lead:
    lead = Lead(**payload.model_dump())
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def list_leads(session: Session) -> list[Lead]:
    statement = select(Lead).order_by(Lead.created_at.desc())
    return list(session.exec(statement))


def mark_booking_link_sent(session: Session, lead: Lead) -> Lead:
    lead.booking_link_sent = True
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def mark_owner_notified(session: Session, lead: Lead) -> Lead:
    lead.owner_notified = True
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead