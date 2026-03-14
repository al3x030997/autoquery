"""Auth routes: register, login, refresh."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from autoquery.api.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from autoquery.api.deps import RateLimiter, get_session_id
from autoquery.api.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from autoquery.database.db import get_db
from autoquery.database.models import InteractionEvent, Manuscript, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_auth_rate_limit = RateLimiter(max_calls=5, period_seconds=900, key_prefix="auth")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
    session_id: str = Depends(get_session_id),
    _rl: None = Depends(_auth_rate_limit),
):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Link anonymous session data to the new user
    if session_id:
        linked = _link_session_to_user(db, session_id, user.id)
        if linked:
            logger.info("Linked %d manuscripts from session %s to user %d", linked, session_id, user.id)

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


def _link_session_to_user(db: Session, session_id: str, user_id: int) -> int:
    """Link anonymous manuscripts and events from a session to a newly registered user."""
    manuscripts = (
        db.query(Manuscript)
        .filter(Manuscript.session_id == session_id, Manuscript.user_id.is_(None))
        .all()
    )
    if not manuscripts:
        return 0

    manuscript_ids = [m.id for m in manuscripts]
    for m in manuscripts:
        m.user_id = user_id

    # Link orphaned events for those manuscripts
    db.query(InteractionEvent).filter(
        InteractionEvent.manuscript_id.in_(manuscript_ids),
        InteractionEvent.user_id.is_(None),
    ).update({InteractionEvent.user_id: user_id}, synchronize_session="fetch")

    db.commit()
    return len(manuscripts)


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
    _rl: None = Depends(_auth_rate_limit),
):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: dict,
    db: Session = Depends(get_db),
):
    token = body.get("refresh_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="refresh_token required")

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not a refresh token")

    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )
