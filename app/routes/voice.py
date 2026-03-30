from fastapi import APIRouter, Depends, Form, Response
from sqlmodel import Session
from app.db import get_session
from app.schemas import LeadCreate
from app.services.lead_service import create_lead, mark_booking_link_sent, mark_owner_notified
from app.services.twilio_service import (
    build_welcome_response,
    build_booking_followup_response,
    build_question_response,
    build_callback_response,
    build_completion_response,
    send_sms,
)
from app.config import settings

router = APIRouter(prefix="/voice", tags=["voice"])


def simple_intent_classifier(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ["book", "appointment", "haircut", "cut", "trim", "fade"]):
        return "booking"
    if any(word in lowered for word in ["hours", "open", "close", "where", "located", "price", "cost"]):
        return "question"
    if any(word in lowered for word in ["callback", "call me back", "call back"]):
        return "callback"
    return "booking"


@router.post("/incoming")
def incoming_call():
    return Response(content=build_welcome_response(), media_type="application/xml")


@router.post("/handle-intent")
def handle_intent(From: str = Form(default=""), SpeechResult: str = Form(default="")):
    intent = simple_intent_classifier(SpeechResult)

    if intent == "question":
        xml = build_question_response()
    elif intent == "callback":
        xml = build_callback_response()
    else:
        xml = build_booking_followup_response()

    return Response(content=xml, media_type="application/xml")


@router.post("/capture-booking")
def capture_booking(
    session: Session = Depends(get_session),
    From: str = Form(default=""),
    SpeechResult: str = Form(default=""),
):
    lead = create_lead(
        session,
        LeadCreate(
            phone_number=From,
            intent="booking",
            notes=SpeechResult,
        ),
    )

    customer_text = f"Thanks for calling {settings.shop_name}. Book here: {settings.shop_booking_link}"
    owner_text = f"New missed-call lead for {settings.shop_name}: Phone {lead.phone_number}. Details: {lead.notes}"

    if settings.twilio_phone_number and settings.shop_booking_link:
        send_sms(lead.phone_number, customer_text)
        mark_booking_link_sent(session, lead)

    if settings.twilio_phone_number and settings.owner_phone_number:
        send_sms(settings.owner_phone_number, owner_text)
        mark_owner_notified(session, lead)

    return Response(content=build_completion_response(), media_type="application/xml")