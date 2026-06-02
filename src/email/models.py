from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base
from src.email.enums import EmailSendingStatus, EmailType


class PendingEmail(Base):
    __tablename__ = "pending_emails"

    recipient: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    text_body: Mapped[str] = mapped_column(Text, nullable=False)

    email_type: Mapped[EmailType] = mapped_column(SQLEnum(EmailType), nullable=False)

    status: Mapped[str] = mapped_column(
        SQLEnum(EmailSendingStatus),
        nullable=False,
        default=EmailSendingStatus.pending,
        index=True,
    )

    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    triggered_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    recipient_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    triggered_by_user: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[triggered_by],
    )
    recipient_user: Mapped["User | None"] = relationship(  # noqa: F821
        "User",
        foreign_keys=[recipient_user_id],
    )
