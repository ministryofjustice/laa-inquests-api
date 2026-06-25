from typing import Annotated
from datetime import timezone, timedelta, datetime

from passlib.hash import argon2
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi.security import (
    OAuth2PasswordBearer,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from fastapi import HTTPException, Depends, status
from app.adapters.entra_auth_adapter import EntraAuthAdapter
from app.config import Config
from app.ports.entra_auth_port import EntraAuthPort
from app.models.user import User, TokenData
from app.db import get_session
from sqlmodel import Session

import logging

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = Config.SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    return argon2.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    This function runs argon2 salting and hashing via passlib.

    Args:
        password: Password data as a string.

    Returns:
        password: Returns a hashed and salted password using
        passlib argon2.
    """
    return argon2.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        if expires_delta
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def authenticate_user(session, username: str, password: str) -> str | User | bool:
    """
    This function returns the user if they are authenticated against their
    hashed password and exist in the database. Used in service login.

    Args:
        session: Current database session
        username: Username data as a string
        password: Password data as a string

    Returns:
        user: A string that contains the user information to be used
        to create the access token
        False: If user does not exist or if the verify password function
        cannot match the current password with the hashed user password
    """
    user = session.get(User, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        TokenData(username=username)
    except InvalidTokenError:
        logging.warning(f"Invalid Token Authorisation on token {token}")
        raise credentials_exception


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User Disabled",
        )
    return current_user


_http_bearer = HTTPBearer(auto_error=False)


def get_entra_auth_port() -> EntraAuthPort:
    return EntraAuthAdapter(
        tenant_id=Config.ENTRA_TENANT_ID,
        client_id=Config.ENTRA_CLIENT_ID,
    )


def verify_entra_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_http_bearer)],
    entra_auth: Annotated[EntraAuthPort, Depends(get_entra_auth_port)],
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    entra_auth.verify_token(credentials.credentials)
