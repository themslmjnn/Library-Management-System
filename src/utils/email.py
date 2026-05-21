from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

async def _send(subject: str, to_email: str, html_body: str, text_body: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>"
    message["To"] = to_email

    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    validate_certs = settings.ENVIRONMENT == "production"

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.MAIL_HOST,
            port=settings.MAIL_PORT,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            start_tls=True,
            validate_certs=validate_certs,
        )

        logger.info(
            "email_sent", 
            to_email=to_email,
            subject=subject,
        )

    except aiosmtplib.SMTPException as exc:
        logger.error(
            "email_send_failed",
            to=to_email,
            subject=subject,
            error=str(exc),
            error_type=type(exc).__name__,
        )


def _invite_email_html(invite_token: str) -> str:
    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
        <body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:40px 16px;">
            <table width="560" cellpadding="0" cellspacing="0"
                    style="background:#ffffff;border-radius:8px;overflow:hidden;
                            box-shadow:0 1px 4px rgba(0,0,0,.08);">
        
                <!-- Header -->
                <tr><td style="background:#1d4ed8;padding:32px 40px;">
                <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">
                    Library Management System
                </h1>
                </td></tr>
        
                <!-- Body -->
                <tr><td style="padding:40px;text-align:center;">
                <h2 style="margin:0 0 16px;color:#111827;font-size:18px;">
                    You have been invited
                </h2>
                <p style="margin:0 0 32px;color:#374151;font-size:15px;line-height:1.6;text-align:left;">
                    An administrator has created an account for you.
                    Copy the invite token below and submit it along with your email address
                    and a password of your choice to activate your account.
                    This token expires in <strong>{settings.INVITE_TOKEN_EXPIRES_HOURS} hours</strong>.
                </p>
        
                <!-- Token block -->
                <div style="background:#f0f4ff;border:2px solid #1d4ed8;
                            border-radius:8px;padding:24px 32px;">
                    <p style="margin:0 0 8px;color:#6b7280;font-size:12px;
                            text-transform:uppercase;letter-spacing:1px;">
                    Your invite token
                    </p>
                    <span style="font-size:13px;font-weight:700;color:#1d4ed8;
                                word-break:break-all;font-family:monospace;">
                    {invite_token}
                    </span>
                </div>
        
                <p style="margin:32px 0 0;color:#374151;font-size:14px;line-height:1.6;text-align:left;">
                    Submit this token together with your email and chosen password to:<br>
                    <code style="background:#f4f4f5;padding:2px 6px;border-radius:4px;
                                font-size:13px;">
                    POST /auth/activate_with_token
                    </code>
                </p>
        
                <p style="margin:24px 0 0;color:#6b7280;font-size:13px;text-align:left;">
                    If you were not expecting this email, you can safely ignore it.
                </p>
                </td></tr>
        
                <!-- Footer -->
                <tr><td style="padding:24px 40px;border-top:1px solid #e5e7eb;">
                <p style="margin:0;color:#9ca3af;font-size:12px;">
                    {settings.MAIL_FROM_NAME} &mdash; do not reply to this email.
                </p>
                </td></tr>
        
            </table>
            </td></tr>
        </table>
        </body>
        </html>
    """

def _invite_email_text(invite_token: str) -> str:
    return (
        f"You have been invited to the Library Management System.\n\n"
        f"An administrator has created an account for you.\n"
        f"Copy the invite token below and submit it along with your email\n"
        f"and a password of your choice to activate your account.\n\n"
        f"Your invite token:\n\n"
        f"{invite_token}\n\n"
        f"Submit it to: POST /auth/activate_with_token\n\n"
        f"This token expires in {settings.INVITE_TOKEN_EXPIRES_HOURS} hours.\n\n"
        f"If you were not expecting this email, you can safely ignore it."
    )


def _activation_code_html(code: str) -> str:
    return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
        <body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:40px 16px;">
            <table width="560" cellpadding="0" cellspacing="0"
                    style="background:#ffffff;border-radius:8px;overflow:hidden;
                            box-shadow:0 1px 4px rgba(0,0,0,.08);">

                <!-- Header -->
                <tr><td style="background:#1d4ed8;padding:32px 40px;">
                <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">
                    Library Management System
                </h1>
                </td></tr>

                <!-- Body -->
                <tr><td style="padding:40px;text-align:center;">
                <h2 style="margin:0 0 16px;color:#111827;font-size:18px;">
                    Your activation code
                </h2>
                <p style="margin:0 0 32px;color:#374151;font-size:15px;line-height:1.6;">
                    Enter the code below to activate your account.
                    It expires in <strong>{settings.ACTIVATION_CODE_EXPIRES_HOURS} minutes</strong>.
                </p>

                <!-- OTP block -->
                <div style="display:inline-block;background:#f0f4ff;border:2px solid #1d4ed8;
                            border-radius:8px;padding:20px 48px;">
                    <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#1d4ed8;">
                    {code}
                    </span>
                </div>

                <p style="margin:32px 0 0;color:#6b7280;font-size:13px;">
                    If you did not request this code, ignore this email.
                </p>
                </td></tr>

                <!-- Footer -->
                <tr><td style="padding:24px 40px;border-top:1px solid #e5e7eb;">
                <p style="margin:0;color:#9ca3af;font-size:12px;">
                    {settings.MAIL_FROM_NAME} &mdash; do not reply to this email.
                </p>
                </td></tr>

            </table>
            </td></tr>
        </table>
        </body>
        </html>
    """


def _activation_code_text(code: str) -> str:
    return (
        f"Your Library Management System activation code is: {code}\n\n"
        f"It expires in {settings.ACTIVATION_CODE_EXPIRES_HOURS} minutes.\n\n"
        f"If you did not request this, ignore this email."
    )


async def send_invite_email(email: str, raw_invite_token: str) -> None:
    await _send(
        subject="You have been invited to the Library Management System",
        to_email=email,
        html_body=_invite_email_html(raw_invite_token),
        text_body=_invite_email_text(raw_invite_token),
    )


async def send_account_activation_code(email: str, code: str) -> None:
    await _send(
        subject="Your Library activation code",
        to_email=email,
        html_body=_activation_code_html(code),
        text_body=_activation_code_text(code),
    )