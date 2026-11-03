from __future__ import annotations
import base64, hashlib, hmac, json, re, secrets, time
from fastapi import Depends, HTTPException, Header
from sqlalchemy.orm import Session
from .db import get_db
from . import models as m
from .config import SECRET_KEY, ACCESS_TOKEN_MINUTES

EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+-]+@adypu\.edu\.in$", re.I)

def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.fullmatch(email.strip()))

def _pbkdf(secret: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt, 180_000)
    return base64.urlsafe_b64encode(salt + digest).decode()

def verify_hash(secret: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", secret.encode(), raw[:16], 180_000), raw[16:])
    except Exception:
        return False

def hash_pw(password: str) -> str:
    return _pbkdf(password)

def check_pw(password: str, encoded: str) -> bool:
    return verify_hash(password, encoded)

def hash_code(code: str) -> str:
    return _pbkdf(code)

def check_code(code: str, encoded: str) -> bool:
    return verify_hash(code, encoded)

def new_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"

def make_token(user_id: int) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + ACCESS_TOKEN_MINUTES * 60}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return raw + "." + sig

def read_token(token: str) -> int:
    try:
        raw, sig = token.split(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected): raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
        if int(payload["exp"]) < int(time.time()): raise ValueError("expired")
        return int(payload["sub"])
    except Exception:
        raise HTTPException(401, "Your session has expired. Please sign in again.")

def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> m.User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Sign in to continue.")
    uid = read_token(authorization[7:].strip())
    user = db.get(m.User, uid)
    if not user: raise HTTPException(401, "Account not found. Please sign in again.")
    return user
