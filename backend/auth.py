"""Simplest login: hash passwords with bcrypt, hand out a signed JWT pass.

A JWT is a small signed note ("user 5, expires in 7 days"). The server signs it
with JWT_SECRET so nobody can fake one. We check it on every protected request.
"""
import os
from datetime import datetime, timezone, timedelta

import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import db

JWT_SECRET = os.getenv("JWT_SECRET", "change_me")  # set a real value in .env
_bearer = HTTPBearer()


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode()[:72], bcrypt.gensalt()).decode()


def check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode()[:72], hashed.encode())
    except Exception:
        return False


def make_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def current_user(creds: HTTPAuthorizationCredentials = Depends(_bearer)):
    """Runs before protected endpoints. Returns the logged-in user or raises 401."""
    try:
        payload = jwt.decode(creds.credentials, JWT_SECRET, algorithms=["HS256"])
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user
