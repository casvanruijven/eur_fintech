"""User accounts: registration, login/logout, and profile (/me)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import (
    COOKIE_NAME,
    CurrentUser,
    cookie_kwargs,
    create_token,
    hash_password,
    verify_password,
)
from app.database import get_session
from app.models import User, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api", tags=["users"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, session: SessionDep) -> User:
    """Create a new account with email + name + password."""
    if await _get_by_email(session, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        password_hash=hash_password(body.password),
        accountant_email=body.accountant_email,
    )
    session.add(user)
    await session.flush()  # populate generated fields before the response
    return user


@router.post("/login")
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    response: Response,
    session: SessionDep,
) -> dict:
    """Verify credentials, set the auth cookie, and return the token.

    Uses the OAuth2 form so Swagger's "Authorize" button works: the email goes
    in the ``username`` field.
    """
    user = await _get_by_email(session, form.username)
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    token = create_token(user)
    response.set_cookie(COOKIE_NAME, token, **cookie_kwargs())
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    response.delete_cookie(COOKIE_NAME, **cookie_kwargs())
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
async def get_me(user: CurrentUser) -> User:
    return user


@router.put("/me", response_model=UserOut)
async def update_me(body: UserUpdate, user: CurrentUser, session: SessionDep) -> User:
    """Update the caller's own profile (name / accountant email)."""
    data = body.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(user, field, value)
    session.add(user)
    await session.flush()
    return user
