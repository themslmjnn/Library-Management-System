from enum import Enum


class EmailType(str, Enum):
    invite = "invite"
    password_reset_admin = "password_reset_admin"
    activation_with_token = "activation_with_token"
    activation_with_code = "activation_with_code"
    # account_deactivation = "account_deactivation"


class EmailSendingStatus(str, Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
