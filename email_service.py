

import os
import logging
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

load_dotenv()

logger = logging.getLogger(__name__)


def send_email(to_email, subject, html_content):
    if not to_email:
        logger.warning("Email not sent: recipient email is missing.")
        return False

    api_key = os.getenv("SENDGRID_API_KEY")
    sender = os.getenv("MAIL_FROM_EMAIL")

    if not api_key or not sender:
        logger.error("SendGrid configuration is incomplete.")
        return False

    try:
        message = Mail(
            from_email=sender,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )

        sg = SendGridAPIClient(api_key=api_key)
        response = sg.send(message)

        if response.status_code == 202:
            logger.info("Email accepted by SendGrid.")
            return True

        logger.error(
            "SendGrid returned status code: %s",
            response.status_code
        )
        return False

    except Exception:
        logger.exception("Email sending failed.")
        return False
