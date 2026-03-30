from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from app.config import settings

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


def build_welcome_response() -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/voice/handle-intent",
        method="POST",
        speech_timeout="auto",
    )
    gather.say(
        f"Hi, this is {settings.shop_name}. Everyone is with clients right now, but I can help. "
        "Are you looking to book an appointment, ask a quick question, or leave a callback request?"
    )
    response.append(gather)
    response.redirect("/voice/incoming")
    return str(response)


def build_booking_followup_response() -> str:
    response = VoiceResponse()
    gather = Gather(
        input="speech",
        action="/voice/capture-booking",
        method="POST",
        speech_timeout="auto",
    )
    gather.say(
        "Got it. Please say your name, the service you want, any preferred barber, and the day or time that works best for you."
    )
    response.append(gather)
    response.say("Sorry, I did not catch that. Please call back or use the booking link we text you.")
    return str(response)


def build_question_response() -> str:
    response = VoiceResponse()
    response.say(
        f"Our hours are {settings.shop_hours}. We are located in {settings.shop_address}. "
        "If you would like, we can also text you the booking link. Goodbye."
    )
    response.hangup()
    return str(response)


def build_callback_response() -> str:
    response = VoiceResponse()
    response.say("No problem. We will pass your callback request to the shop. Goodbye.")
    response.hangup()
    return str(response)


def build_completion_response() -> str:
    response = VoiceResponse()
    response.say("Perfect. We will text you the booking link now and send your request to the shop. Goodbye.")
    response.hangup()
    return str(response)


def send_sms(to_phone: str, body: str):
    return client.messages.create(
        body=body,
        from_=settings.twilio_phone_number,
        to=to_phone,
    )