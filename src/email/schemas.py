from datetime import datetime

from pydantic import field_serializer

from src.utils.base_schema import BaseSchema


class PendingEmailResponse(BaseSchema):
    id: int
    recipient: str
    subject: str
    email_type: str
    status: str
    retry_count: int
    last_error: str | None
    sent_at: datetime | None
    triggered_by: int | None
    recipient_user_id: int | None
    created_at: datetime

    @field_serializer("created_at", "sent_at")
    def serialize_datetime(self, value: datetime) -> str:
        return value.strftime("%d %b %Y, %H:%M")
