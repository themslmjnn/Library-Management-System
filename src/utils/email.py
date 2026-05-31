# import httpx

# from src.core.config import settings
# from src.core.logging import get_logger

# logger = get_logger(__name__)


# async def _send(
#     subject: str,
#     to_email: str,
#     html_body: str,
#     text_body: str,
# ) -> None:

#     payload = {
#         "from": f"{settings.MAIL_FROM_NAME} <{settings.MAIL_FROM}>",
#         "to": [to_email],
#         "subject": subject,
#         "html": html_body,
#         "text": text_body,
#     }

#     headers = {
#         "Authorization": f"Bearer {settings.RESEND_API_KEY}",
#         "Content-Type": "application/json",
#     }

#     try:
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 "https://api.resend.com/emails",
#                 json=payload,
#                 headers=headers,
#                 timeout=10.0,
#             )

#         response.raise_for_status()

#         logger.info(
#             "email_sent",
#             to_email=to_email,
#             subject=subject,
#         )

#     except httpx.HTTPStatusError as exc:
#         logger.error(
#             "email_send_failed",
#             to_email=to_email,
#             subject=subject,
#             status_code=exc.response.status_code,
#             response=exc.response.text,
#         )

#     except Exception as exc:
#         logger.error(
#             "email_send_failed",
#             to_email=to_email,
#             subject=subject,
#             error=str(exc),
#             error_type=type(exc).__name__,
#         )


# def _invite_email_html(invite_token: str) -> str:
#     activation_link = f"{settings.APP_URL}/activate_with_token?token={invite_token}"

#     return f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
#         <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">

#             <h1 style="color:#1d4ed8;">
#                 Library Management System
#             </h1>

#             <h2>You have been invited</h2>

#             <p>
#                 An administrator created an account for you.
#             </p>

#             <p>
#                 Click the button below to activate your account.
#                 This invitation expires in
#                 <strong>{settings.INVITE_TOKEN_EXPIRES_HOURS} hours</strong>.
#             </p>

#             <div style="margin:40px 0;text-align:center;">
#                 <a href="{activation_link}"
#                     style="
#                         background:#1d4ed8;
#                         color:white;
#                         padding:14px 28px;
#                         border-radius:6px;
#                         text-decoration:none;
#                         font-weight:bold;
#                     ">
#                     Activate Account
#                 </a>
#             </div>

#             <p style="font-size:13px;color:#6b7280;">
#                 If you were not expecting this email, ignore it.
#             </p>

#         </div>
#     </body>
#     </html>
#     """


# def _invite_email_text(invite_token: str) -> str:
#     activation_link = f"{settings.APP_URL}/activate_with_token?token={invite_token}"

#     return (
#         f"You have been invited to the Library Management System.\n\n"
#         f"Activate your account using the link below:\n\n"
#         f"{activation_link}\n\n"
#         f"This invitation expires in "
#         f"{settings.INVITE_TOKEN_EXPIRES_HOURS} hours.\n\n"
#         f"If you were not expecting this email, ignore it."
#     )


# async def send_invite_email(
#     email: str,
#     raw_invite_token: str,
# ) -> None:
#     await _send(
#         subject="Activate your Library account",
#         to_email=email,
#         html_body=_invite_email_html(raw_invite_token),
#         text_body=_invite_email_text(raw_invite_token),
#     )


# def _activation_code_html(code: str) -> str:
#     return f"""
#         <!DOCTYPE html>
#         <html lang="en">
#         <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
#         <body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif;">
#         <table width="100%" cellpadding="0" cellspacing="0">
#             <tr><td align="center" style="padding:40px 16px;">
#             <table width="560" cellpadding="0" cellspacing="0"
#                     style="background:#ffffff;border-radius:8px;overflow:hidden;
#                             box-shadow:0 1px 4px rgba(0,0,0,.08);">

#                 <!-- Header -->
#                 <tr><td style="background:#1d4ed8;padding:32px 40px;">
#                 <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:600;">
#                     Library Management System
#                 </h1>
#                 </td></tr>

#                 <!-- Body -->
#                 <tr><td style="padding:40px;text-align:center;">
#                 <h2 style="margin:0 0 16px;color:#111827;font-size:18px;">
#                     Your activation code
#                 </h2>
#                 <p style="margin:0 0 32px;color:#374151;font-size:15px;line-height:1.6;">
#                     Enter the code below to activate your account.
#                     It expires in <strong>{settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes</strong>.
#                 </p>

#                 <!-- OTP block -->
#                 <div style="display:inline-block;background:#f0f4ff;border:2px solid #1d4ed8;
#                             border-radius:8px;padding:20px 48px;">
#                     <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#1d4ed8;">
#                     {code}
#                     </span>
#                 </div>

#                 <p style="margin:32px 0 0;color:#6b7280;font-size:13px;">
#                     If you did not request this code, ignore this email.
#                 </p>
#                 </td></tr>

#                 <!-- Footer -->
#                 <tr><td style="padding:24px 40px;border-top:1px solid #e5e7eb;">
#                 <p style="margin:0;color:#9ca3af;font-size:12px;">
#                     {settings.MAIL_FROM_NAME} &mdash; do not reply to this email.
#                 </p>
#                 </td></tr>

#             </table>
#             </td></tr>
#         </table>
#         </body>
#         </html>
#     """


# def _activation_code_text(code: str) -> str:
#     return (
#         f"Your Library Management System activation code is: {code}\n\n"
#         f"It expires in {settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes.\n\n"
#         f"If you did not request this, ignore this email."
#     )


# async def send_account_activation_code(email: str, code: str) -> None:
#     await _send(
#         subject="Your Library activation code",
#         to_email=email,
#         html_body=_activation_code_html(code),
#         text_body=_activation_code_text(code),
#     )


# def _reset_password_html(reset_password_token: str) -> str:
#     reset_password_link = (
#         f"{settings.APP_URL}/reset_password?token={reset_password_token}"
#     )

#     return f"""
#     <!DOCTYPE html>
#     <html lang="en">
#     <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
#         <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">

#             <h1 style="color:#1d4ed8;">
#                 Library Management System
#             </h1>

#             <p>
#                 Click the button below to reset your password.
#                 This link expires in
#                 <strong>{settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes</strong>.
#             </p>

#             <div style="margin:40px 0;text-align:center;">
#                 <a href="{reset_password_link}"
#                     style="
#                         background:#1d4ed8;
#                         color:white;
#                         padding:14px 28px;
#                         border-radius:6px;
#                         text-decoration:none;
#                         font-weight:bold;
#                     ">
#                     Reset Password
#                 </a>
#             </div>

#             <p style="font-size:13px;color:#6b7280;">
#                 If you were not expecting this email, ignore it.
#             </p>

#         </div>
#     </body>
#     </html>
#     """


# def _reset_password_text(reset_password_token: str) -> str:
#     reset_password_link = (
#         f"{settings.APP_URL}/reset_password?token={reset_password_token}"
#     )

#     return (
#         f"Library Management System.\n\n"
#         f"Reset your account password using the link below:\n\n"
#         f"{reset_password_link}\n\n"
#         f"This link expires in "
#         f"{settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes.\n\n"
#         f"If you were not expecting this email, ignore it."
#     )


# async def send_reset_password_token(email: str, raw_reset_token: str) -> None:
#     await _send(
#         subject="Your Library reset password link",
#         to_email=email,
#         html_body=_reset_password_html(raw_reset_token),
#         text_body=_reset_password_text(raw_reset_token),
#     )

# src/utils/email.py

import httpx

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core transport
# ---------------------------------------------------------------------------


async def _send(
    subject: str,
    to_email: str,
    html_body: str,
    text_body: str,
) -> None:
    """
    Sends an email via Resend. Raises on failure — callers decide
    whether to swallow or propagate. Never call this directly from
    a route; use _send_safe for fire-and-forget background tasks.
    """
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


async def _send_safe(coro, **log_context) -> None:
    """
    Wraps an email coroutine for use with asyncio.create_task.
    Catches and logs all exceptions so the event loop never sees
    an unhandled exception from a background task.

    Use this ONLY for public flows where failure is intentionally
    non-fatal and non-visible to the caller (enumeration protection).

    Admin/staff flows use PendingEmail table instead.
    """
    try:
        await coro
    except Exception as exc:
        logger.error(
            "background_email_task_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            **log_context,
        )


# ---------------------------------------------------------------------------
# Invite email (used by admin and staff — stored in PendingEmail)
# ---------------------------------------------------------------------------


def build_invite_email(invite_token: str) -> tuple[str, str, str]:
    """
    Returns (subject, html_body, text_body).
    Called by the service before inserting PendingEmail record.
    """
    activation_link = f"{settings.APP_URL}/activate_with_token?token={invite_token}"
    subject = "Activate your Library account"
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
        <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">
            <h1 style="color:#1d4ed8;">Library Management System</h1>
            <h2>You have been invited</h2>
            <p>An administrator created an account for you.</p>
            <p>
                Click the button below to activate your account.
                This invitation expires in
                <strong>{settings.INVITE_TOKEN_EXPIRES_HOURS} hours</strong>.
            </p>
            <div style="margin:40px 0;text-align:center;">
                <a href="{activation_link}"
                    style="background:#1d4ed8;color:white;padding:14px 28px;
                           border-radius:6px;text-decoration:none;font-weight:bold;">
                    Activate Account
                </a>
            </div>
            <p style="font-size:13px;color:#6b7280;">
                If you were not expecting this email, ignore it.
            </p>
        </div>
    </body>
    </html>
    """
    text = (
        f"You have been invited to the Library Management System.\n\n"
        f"Activate your account using the link below:\n\n"
        f"{activation_link}\n\n"
        f"This invitation expires in {settings.INVITE_TOKEN_EXPIRES_HOURS} hours.\n\n"
        f"If you were not expecting this email, ignore it."
    )
    return subject, html, text


async def send_invite_email(email: str, raw_invite_token: str) -> None:
    subject, html, text = build_invite_email(raw_invite_token)
    await _send(subject=subject, to_email=email, html_body=html, text_body=text)


# ---------------------------------------------------------------------------
# Activation code (public self-registration — fire and forget)
# ---------------------------------------------------------------------------


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
                It expires in <strong>{settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes</strong>.
            </p>
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
        f"It expires in {settings.ACTIVATION_CODE_EXPIRES_MINUTES} minutes.\n\n"
        f"If you did not request this, ignore this email."
    )


async def send_account_activation_code(email: str, code: str) -> None:
    await _send(
        subject="Your Library activation code",
        to_email=email,
        html_body=_activation_code_html(code),
        text_body=_activation_code_text(code),
    )


# ---------------------------------------------------------------------------
# Already-registered notice (enumeration protection for public registration)
# ---------------------------------------------------------------------------


def _already_registered_html() -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
        <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">
            <h1 style="color:#1d4ed8;">Library Management System</h1>
            <h2>Registration attempt detected</h2>
            <p>
                Someone tried to register a new account using your email address.
                If this was you, your account already exists —
                <a href="{settings.APP_URL}/login">sign in here</a>.
            </p>
            <p>
                If this was not you, no action is needed.
                Your account and password have not been changed.
            </p>
            <p style="font-size:13px;color:#6b7280;">
                If you are concerned, consider changing your password.
            </p>
        </div>
    </body>
    </html>
    """


def _already_registered_text() -> str:
    return (
        f"Library Management System.\n\n"
        f"Someone tried to register a new account using your email address.\n\n"
        f"If this was you, your account already exists. Sign in at:\n"
        f"{settings.APP_URL}/login\n\n"
        f"If this was not you, no action is needed. "
        f"Your account and password have not been changed.\n\n"
        f"If you are concerned, consider changing your password."
    )


async def send_already_registered_email(email: str) -> None:
    await _send(
        subject="Someone tried to register with your email",
        to_email=email,
        html_body=_already_registered_html(),
        text_body=_already_registered_text(),
    )


# ---------------------------------------------------------------------------
# Password reset (admin-initiated — stored in PendingEmail)
# ---------------------------------------------------------------------------


def build_reset_password_email(reset_password_token: str) -> tuple[str, str, str]:
    """
    Returns (subject, html_body, text_body).
    Called by the service before inserting PendingEmail record.
    """
    reset_link = f"{settings.APP_URL}/reset_password?token={reset_password_token}"
    subject = "Your Library reset password link"
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
        <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">
            <h1 style="color:#1d4ed8;">Library Management System</h1>
            <p>
                An administrator has requested a password reset for your account.
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
                If you were not expecting this email, contact your administrator.
            </p>
        </div>
    </body>
    </html>
    """
    text = (
        f"Library Management System.\n\n"
        f"An administrator has requested a password reset for your account.\n\n"
        f"Reset your password using the link below:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes.\n\n"
        f"If you were not expecting this email, contact your administrator."
    )
    return subject, html, text


async def send_reset_password_token(email: str, raw_reset_token: str) -> None:
    subject, html, text = build_reset_password_email(raw_reset_token)
    await _send(subject=subject, to_email=email, html_body=html, text_body=text)


# ---------------------------------------------------------------------------
# Public forgot password (fire and forget — enumeration protected)
# ---------------------------------------------------------------------------


def _forgot_password_html(reset_token: str) -> str:
    reset_link = f"{settings.APP_URL}/reset_password?token={reset_token}"
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <body style="font-family: Arial, sans-serif; background:#f4f4f5; padding:40px;">
        <div style="max-width:560px;margin:auto;background:white;padding:40px;border-radius:8px;">
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


def _forgot_password_text(reset_token: str) -> str:
    reset_link = f"{settings.APP_URL}/reset_password?token={reset_token}"
    return (
        f"You requested a password reset for your Library Management System account.\n\n"
        f"Reset your password using the link below:\n\n"
        f"{reset_link}\n\n"
        f"This link expires in {settings.RESET_PASSWORD_EXPIRES_MINUTES} minutes.\n\n"
        f"If you did not request this, ignore this email. "
        f"Your password has not been changed."
    )


async def send_forgot_password_email(email: str, raw_reset_token: str) -> None:
    await _send(
        subject="Your Library password reset link",
        to_email=email,
        html_body=_forgot_password_html(raw_reset_token),
        text_body=_forgot_password_text(raw_reset_token),
    )
