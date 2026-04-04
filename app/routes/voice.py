from fastapi import APIRouter, Depends, Form, Response
from sqlmodel import Session
from app.db import get_session
from app.schemas import LeadCreate
from app.services.lead_service import create_lead, mark_booking_link_sent, mark_owner_notified
from app.services.twilio_service import send_sms
from app.services.ai_service import analyze_customer_turn
from app.config import settings
from twilio.twiml.voice_response import VoiceResponse, Gather

router = APIRouter(prefix="/voice", tags=["voice"])

CALL_STATE = {}


def full_url(path: str) -> str:
    return f"{settings.base_url.rstrip('/')}{path}"


def gather_response(prompt_text: str, action_path: str) -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action=full_url(action_path),
        method="POST",
        speech_timeout="auto",
    )
    gather.say(prompt_text)
    response.append(gather)
    response.say("Sorry, I did not catch that. Please call back and try again.")
    response.hangup()
    return str(response)


def merge_field(old_value, new_value):
    return new_value if new_value not in (None, "", "Unknown") else old_value


def empty_state():
    return {
        "caller_name": None,
        "intent": "booking",
        "service_requested": None,
        "preferred_barber": None,
        "preferred_time": None,
        "notes": [],
    }


@router.post("/incoming")
def incoming_call(From: str = Form(default="")):
    if From:
        CALL_STATE[From] = empty_state()

    greeting = (
        f"Hi, this is {settings.shop_name}. Everyone is with clients right now, but I can help. "
        "What can I get you today?"
    )
    return Response(content=gather_response(greeting, "/voice/collect"), media_type="application/xml")


@router.post("/collect")
def collect_turn(
    session: Session = Depends(get_session),
    From: str = Form(default=""),
    SpeechResult: str = Form(default=""),
):
    result = analyze_customer_turn(SpeechResult)

    if From not in CALL_STATE:
        CALL_STATE[From] = empty_state()

    state = CALL_STATE[From]
    state["caller_name"] = merge_field(state["caller_name"], result.get("caller_name"))
    state["intent"] = merge_field(state["intent"], result.get("intent", "booking"))
    state["service_requested"] = merge_field(state["service_requested"], result.get("service_requested"))
    state["preferred_barber"] = merge_field(state["preferred_barber"], result.get("preferred_barber"))
    state["preferred_time"] = merge_field(state["preferred_time"], result.get("preferred_time"))

    if SpeechResult:
        state["notes"].append(SpeechResult)

    # only require service + time for MVP
    missing_service = not state["service_requested"]
    missing_time = not state["preferred_time"]

    if missing_service:
        return Response(
            content=gather_response("Got you — what service are you looking for?", "/voice/collect"),
            media_type="application/xml",
        )

    if missing_time:
        return Response(
            content=gather_response("Perfect — what time were you thinking?", "/voice/collect"),
            media_type="application/xml",
        )

    combined_notes = " | ".join(state["notes"])

    lead = create_lead(
        session,
        LeadCreate(
            phone_number=From,
            caller_name=state["caller_name"],
            intent=state["intent"],
            service_requested=state["service_requested"],
            preferred_barber=state["preferred_barber"],
            preferred_time=state["preferred_time"],
            notes=combined_notes,
        ),
    )

    customer_text = (
        f"Hey {lead.caller_name or ''}! We got your request for a "
        f"{lead.service_requested or 'service'} "
        f"{'at ' + lead.preferred_time if lead.preferred_time else ''}. "
        f"Book here to lock it in: {settings.shop_booking_link}"
    )

    owner_text = (
    f"📞 New missed call lead\n\n"
    f"👤 {lead.caller_name or 'Unknown'}\n"
    f"💈 {lead.service_requested or 'Unknown service'}\n"
    f"⏰ {lead.preferred_time or 'No time given'}\n"
    f"✂️ {lead.preferred_barber or 'No preference'}\n\n"
    f"📱 {lead.phone_number}"
    )

    try:
        if settings.twilio_phone_number and settings.shop_booking_link:
            customer_msg = send_sms(lead.phone_number, customer_text)
            print("CUSTOMER SMS SID:", customer_msg.sid)
            mark_booking_link_sent(session, lead)
    except Exception as e:
        print("CUSTOMER SMS ERROR:", str(e))

    try:
        if settings.twilio_phone_number and settings.owner_phone_number:
            owner_msg = send_sms(settings.owner_phone_number, owner_text)
            print("OWNER SMS SID:", owner_msg.sid)
            mark_owner_notified(session, lead)
    except Exception as e:
        print("OWNER SMS ERROR:", str(e))

    CALL_STATE.pop(From, None)

    response = VoiceResponse()
    response.say("Perfect, I’ve got everything I need. I’ll pass this to the shop and they’ll take care of you. Talk soon.")
    response.hangup()
    return Response(content=str(response), media_type="application/xml")