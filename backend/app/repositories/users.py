import uuid
from datetime import datetime

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models import EmailKind, EmailOutbox, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalars(
            select(User).where(func.lower(User.email) == email.strip().lower())
        ).one_or_none()

    def add(self, user: User) -> None:
        self.db.add(user)

    def has_recent_email(self, user_id: uuid.UUID, kind: EmailKind, since: datetime) -> bool:
        """Whether an email of `kind` was queued for this user at or after `since`."""
        return bool(
            self.db.scalar(
                select(
                    exists().where(
                        EmailOutbox.user_id == user_id,
                        EmailOutbox.kind == kind,
                        EmailOutbox.created_at >= since,
                    )
                )
            )
        )
