import httpx

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


async def _send(
    subject: str,
    to_email: str,
    html_body: str,
    text_body: str,
) -> None:
    payload = {
        "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.resend.com/emails",
            json=payload,
            headers=headers,
            timeout=10.0,
        )

    response.raise_for_status()

    logger.info("email_sent", to_email=to_email, subject=subject)


async def send_safe(coro, **log_context) -> None:
    try:
        await coro
    except Exception as exc:
        logger.error(
            "background_email_task_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            **log_context,
        )


def build_activation_code_email(code: str) -> tuple[str, str, str]:
    subject = "Your Library activation code"

    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width,initial-scale=1">
        </head>
        <body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0">
            <tr><td align="center" style="padding:40px 16px;">
            <table width="560" cellpadding="0" cellspacing="0"
                    style="background:#ffffff;border-radius:8px;overflow:hidden;
                            box-shadow:0 1px 4px rgba(0,0,0,.08);">
                <tr><td style="background:#1d4ed8;padding:32px 40px;">
                    <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">
                        Library Management System
                    </h1>
                </td></tr>
                <tr><td style="padding:40px;text-align:center;">
                    <h2 style="margin:0 0 16px;color:#111827;font-size:18px;">
                        Your activation code
                    </h2>
                    <p style="margin:0 0 32px;color:#374151;font-size:15px;line-height:1.6;">
                        Enter the code below to activate your account.
                        It expires in
                        <strong>{settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes</strong>.
                    </p>
                    <div style="display:inline-block;background:#f0f4ff;
                                border:2px solid #1d4ed8;border-radius:8px;
                                padding:20px 48px;">
                        <span style="font-size:36px;font-weight:700;
                                    letter-spacing:10px;color:#1d4ed8;">
                            {code}
                        </span>
                    </div>
                    <p style="margin:32px 0 0;color:#6b7280;font-size:13px;">
                        If you did not request this code, ignore this email.
                    </p>
                </td></tr>
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

    text = (
        f"Your Library Management System activation code is: {code}\n\n"
        f"It expires in {settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes.\n\n"
        f"If you did not request this, ignore this email."
    )

    return subject, html, text


async def send_account_activation_code(email: str, code: str) -> None:
    subject, html, text = build_activation_code_email(code)

    await _send(subject=subject, to_email=email, html_body=html, text_body=text)


async def send_already_registered_email(email: str) -> None:
    forgot_password_link = f"{settings.APP_URL}/auth/forgot_password"

    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
            <div style="max-width:560px;margin:auto;background:white;
                        padding:40px;border-radius:8px;">
                <h1 style="color:#1d4ed8;">Library Management System</h1>
                <h2>Registration attempt on your account</h2>
                <p>
                    Someone tried to create a new account using your email address.
                </p>
                <p>
                    If this was you, your account already exists.
                    You can sign in or reset your password using the link below.
                </p>
                <div style="margin:40px 0;text-align:center;">
                    <a href="{forgot_password_link}"
                        style="background:#1d4ed8;color:white;padding:14px 28px;
                            border-radius:6px;text-decoration:none;font-weight:bold;">
                        Reset Password
                    </a>
                </div>
                <p>
                    If this was not you, no action is needed.
                    Your account and password have not been changed.
                </p>
                <p style="font-size:13px;color:#6b7280;">
                    If you are concerned about your account security,
                    consider changing your password.
                </p>
            </div>
        </body>
        </html>
    """

    text = (
        f"Library Management System.\n\n"
        f"Someone tried to create a new account using your email address.\n\n"
        f"If this was you, your account already exists. "
        f"Reset your password at:\n{forgot_password_link}\n\n"
        f"If this was not you, no action is needed. "
        f"Your account and password have not been changed."
    )

    await _send(
        subject="Someone tried to register with your email",
        to_email=email,
        html_body=html,
        text_body=text,
    )

async def send_forgot_password_email(
    email: str,
    raw_reset_token: str,
) -> None:
    reset_link = (
        f"{settings.APP_URL}/auth/reset_password?token={raw_reset_token}"
    )
 
    html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
            <div style="max-width:560px;margin:auto;background:white;
                        padding:40px;border-radius:8px;">
                <h1 style="color:#1d4ed8;">Library Management System</h1>
                <p>
                    You requested a password reset for your account.
                    Click the button below to set a new password.
                    This link expires in
                    <strong>{settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes</strong>.
                </p>
                <div style="margin:40px 0;text-align:center;">
                    <a href="{reset_link}"
                        style="background:#1d4ed8;color:white;padding:14px 28px;
                            border-radius:6px;text-decoration:none;font-weight:bold;">
                        Reset Password
                    </a>
                </div>
                <p style="font-size:13px;color:#6b7280;">
                    If you did not request this, ignore this email.
                    Your password has not been changed.
                </p>
            </div>
        </body>
        </html>
    """
 
    text = (
        f"You requested a password reset for your "
        f"Library Management System account.\n\n"
        f"Reset your password using the link below:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes.\n\n"
        f"If you did not request this, ignore this email. "
        f"Your password has not been changed."
    )
 
    await _send(
        subject="Your Library password reset link",
        to_email=email,
        html_body=html,
        text_body=text,
    )

async def send_password_changed_confirmation(email: str) -> None:
    html = """
        <!DOCTYPE html>
        <html lang="en">
        <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
            <div style="max-width:560px;margin:auto;background:white;
                        padding:40px;border-radius:8px;">
                <h1 style="color:#1d4ed8;">Library Management System</h1>
                <h2>Your password was changed</h2>
                <p>
                    Your account password was successfully changed.
                    If you made this change, no action is needed.
                </p>
                <p>
                    If you did not change your password, contact your administrator
                    immediately as your account may be compromised.
                </p>
            </div>
        </body>
        </html>
    """
 
    text = (
        "Library Management System.\n\n"
        "Your account password was successfully changed.\n\n"
        "If you made this change, no action is needed.\n\n"
        "If you did not change your password, contact your administrator "
        "immediately as your account may be compromised."
    )
 
    await _send(
        subject="Your Library password was changed",
        to_email=email,
        html_body=html,
        text_body=text,
    )

async def send_email_change_verification(
    new_email: str,
    code: str,
) -> None:
    """
    Sent to the NEW email address when a user requests an email change.
    The code proves they own the new address before we update the record.
 
    Sent to the new address — not the current one — because we're
    verifying ownership of the destination address.
 
    Fire and forget — if it fails, the user requests again.
    The pending_email on their session is cleared on next request
    or when a new change is initiated.
    """
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
        <div style="max-width:560px;margin:auto;background:white;
                    padding:40px;border-radius:8px;">
            <h1 style="color:#1d4ed8;">Library Management System</h1>
            <h2>Confirm your new email address</h2>
            <p>
                You requested to change your email address.
                Enter the code below to confirm this new address.
                It expires in
                <strong>{settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes</strong>.
            </p>
            <div style="display:inline-block;background:#f0f4ff;
                        border:2px solid #1d4ed8;border-radius:8px;
                        padding:20px 48px;margin:24px 0;">
                <span style="font-size:36px;font-weight:700;
                             letter-spacing:10px;color:#1d4ed8;">
                    {code}
                </span>
            </div>
            <p style="font-size:13px;color:#6b7280;">
                If you did not request this change, ignore this email.
                Your current email address has not been changed.
            </p>
        </div>
    </body>
    </html>
    """
 
    text = (
        f"Library Management System.\n\n"
        f"You requested to change your email address.\n\n"
        f"Your confirmation code is: {code}\n\n"
        f"It expires in {settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes.\n\n"
        f"If you did not request this change, ignore this email. "
        f"Your current email address has not been changed."
    )
 
    await _send(
        subject="Confirm your new Library email address",
        to_email=new_email,
        html_body=html,
        text_body=text,
    )