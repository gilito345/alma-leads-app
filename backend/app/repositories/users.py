import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User


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
