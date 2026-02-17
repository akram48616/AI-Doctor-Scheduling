"""
Notification service stubs for email and SMS.
"""
import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> dict:
    """
    Stub for sending email. Logs the action and returns success.
    TODO: integrate with SendGrid, SES, or other provider.
    """
    try:
        logger.info("send_email called: to=%s subject=%s", to, subject)
        # TODO: integrate with real email provider
        return {"success": True, "message": "Email logged"}
    except Exception as e:
        logger.exception("Failed to send email")
        return {"success": False, "message": str(e)}


def send_sms(number: str, message: str) -> dict:
    """
    Stub for sending SMS. Logs the action and returns success.
    TODO: integrate with Twilio or other provider.
    """
    try:
        logger.info("send_sms called: number=%s message=%s", number, message)
        # TODO: integrate with real SMS provider
        return {"success": True, "message": "SMS logged"}
    except Exception as e:
        logger.exception("Failed to send SMS")
        return {"success": False, "message": str(e)}