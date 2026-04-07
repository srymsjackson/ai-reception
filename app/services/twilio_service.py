"""Twilio outbound messaging helpers."""

from twilio.rest import Client
from app.config import settings

client = Client(settings.twilio_account_sid, settings.twilio_auth_token)


def send_sms(to: str, body: str):
    """Send one outbound SMS from the configured Twilio number."""
    return client.messages.create(
        body=body,
        from_=settings.twilio_phone_number,
        to=to
    )