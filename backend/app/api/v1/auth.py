from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser
from app.db.session import get_db
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse
from app.services.auth import (
    DuplicateUserError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    authenticate_user,
    issue_token_pair,
    register_user,
    revoke_refresh_token,
    rotate_refresh_token,
)


router = APIRouter(prefix="/auth", tags=["authentication"])
SessionDependency = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(registration: RegisterRequest, session: SessionDependency) -> UserResponse:
    try:
        return register_user(session, registration)
    except DuplicateUserError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A user with this {error.field} already exists.",
        ) from error


@router.post("/login", response_model=TokenResponse)
def login(login_request: LoginRequest, session: SessionDependency) -> TokenResponse:
    try:
        user = authenticate_user(session, login_request)
    except (InactiveUserError, InvalidCredentialsError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    token_pair = issue_token_pair(session, user)
    session.commit()
    return token_pair


@router.post("/refresh", response_model=TokenResponse)
def refresh(refresh_request: RefreshRequest, session: SessionDependency) -> TokenResponse:
    try:
        return rotate_refresh_token(session, refresh_request.refresh_token)
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(refresh_request: RefreshRequest, session: SessionDependency) -> None:
    try:
        revoke_refresh_token(session, refresh_request.refresh_token)
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: CurrentUser) -> UserResponse:
    return current_user
