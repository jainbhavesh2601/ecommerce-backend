from sqlmodel import SQLModel, Field, Column
import uuid
from typing import Optional
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timedelta, timezone

class EmailVerificationToken(SQLModel, table=True):
    _tablename_ = "email_verification_tokens"

    id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            primary_key=True,
            default=uuid.uuid4,
            unique=True,
            nullable=False
        )
    )
    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            nullable=False,
            index=True
        )
    )
    token: str = Field(nullable=False, unique=True, index=True, max_length=255)
    expires_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            nullable=False
        )
    )
    is_used: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(
            pg.TIMESTAMP(timezone=True),
            default=lambda: datetime.now(timezone.utc),  # ✅ FIXED
            nullable=False
        )
    )

    @classmethod
    def create_token(cls, user_id: uuid.UUID, expiry_hours: int = 24):
        """Create a new verification token"""
        token_value = str(uuid.uuid4())
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)  # ✅ FIXED
        return cls(
            user_id=user_id,
            token=token_value,
            expires_at=expires_at
        )

    def is_expired(self) -> bool:
        """Check if token is expired"""
        return datetime.now(timezone.utc) > self.expires_at  # ✅ FIXED

    def _repr_(self):
        return f"<EmailVerificationToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"