from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.jwt import create_access_token, hash_password, verify_password
from app.core.settings import get_settings
from app.models import User
from app.schemas.auth import RegisterRequest, TokenResponse
from app.schemas.user import UserRead


class AuthService:
    @staticmethod
    def register_user(db: Session, payload: RegisterRequest) -> User:
        normalized_email = payload.email.lower()
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user is not None:
            raise ValueError("A user with this email already exists")

        user = User(
            email=normalized_email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User | None:
        user = db.query(User).filter(User.email == email.lower()).first()
        if user is None:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    @staticmethod
    def build_token_response(user: User) -> TokenResponse:
        settings = get_settings()
        access_token = create_access_token(user.id)
        return TokenResponse(
            access_token=access_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserRead.model_validate(user),
        )
