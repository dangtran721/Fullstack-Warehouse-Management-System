import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    TokenValidationError,
    create_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse


class DuplicateUserError(Exception):
    def __init__(self, field: str) -> None:
        self.field = field


class InvalidCredentialsError(Exception):
    pass


class InactiveUserError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def register_user(session: Session, registration: RegisterRequest) -> User:
    existing_user = session.scalar(
        select(User).where(
            or_(User.username == registration.username, User.email == str(registration.email))
        )
    )
    if existing_user is not None:
        field = "username" if existing_user.username == registration.username else "email"
        raise DuplicateUserError(field)

    user = User(
        id=uuid.uuid4(),
        username=registration.username,
        email=str(registration.email),
        password_hash=hash_password(registration.password),
        full_name=registration.full_name,
        role=UserRole.STAFF,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise DuplicateUserError("username or email") from error
    session.refresh(user)
    return user


def authenticate_user(session: Session, login: LoginRequest) -> User:
    user = session.scalar(
        select(User).where(or_(User.username == login.identifier, User.email == login.identifier))
    )
    if user is None or not verify_password(login.password, user.password_hash):
        raise InvalidCredentialsError
    if not user.is_active:
        raise InactiveUserError
    return user


def issue_token_pair(session: Session, user: User, family_id: uuid.UUID | None = None) -> TokenResponse:
    settings = get_settings()
    access_token, _ = create_token(
        subject=user.id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    token_family_id = family_id or uuid.uuid4()
    refresh_token, refresh_claims = create_token(
        subject=user.id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
        additional_claims={"family": str(token_family_id)},
    )
    session.add(
        RefreshToken(
            id=uuid.uuid4(),
            user_id=user.id,
            jti=refresh_claims["jti"],
            token_hash=hash_refresh_token(refresh_token),
            family_id=token_family_id,
            expires_at=refresh_claims["exp"],
        )
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


def rotate_refresh_token(session: Session, raw_token: str) -> TokenResponse:
    try:
        claims = decode_token(raw_token, "refresh")
        user_id = uuid.UUID(claims["sub"])
        family_id = uuid.UUID(claims["family"])
    except (KeyError, ValueError, TokenValidationError) as error:
        raise InvalidRefreshTokenError from error

    refresh_token = session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    if (
        refresh_token is None
        or refresh_token.user_id != user_id
        or refresh_token.jti != claims["jti"]
        or refresh_token.family_id != family_id
    ):
        raise InvalidRefreshTokenError

    now = datetime.now(timezone.utc)
    if refresh_token.revoked_at is not None:
        if refresh_token.replaced_by_id is not None:
            session.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.family_id == refresh_token.family_id,
                    RefreshToken.revoked_at.is_(None),
                )
                .values(revoked_at=now)
            )
            session.commit()
        raise InvalidRefreshTokenError

    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError

    refresh_token.revoked_at = now
    token_pair = issue_token_pair(session, user, refresh_token.family_id)
    session.flush()
    replacement = session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(token_pair.refresh_token)
        )
    )
    if replacement is None:
        session.rollback()
        raise InvalidRefreshTokenError
    refresh_token.replaced_by_id = replacement.id
    session.commit()
    return token_pair


def revoke_refresh_token(session: Session, raw_token: str) -> None:
    try:
        claims = decode_token(raw_token, "refresh")
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, TokenValidationError, ValueError) as error:
        raise InvalidRefreshTokenError from error

    refresh_token = session.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if (
        refresh_token is None
        or refresh_token.user_id != user_id
        or refresh_token.jti != claims["jti"]
        or refresh_token.revoked_at
    ):
        raise InvalidRefreshTokenError

    refresh_token.revoked_at = datetime.now(timezone.utc)
    session.commit()
