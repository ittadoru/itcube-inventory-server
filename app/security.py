import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from itsdangerous import BadSignature, URLSafeSerializer

from .config import get_settings

settings = get_settings()


def _api_key_for_bucket(bucket: int) -> str:
    digest = hmac.new(
        settings.api_key_secret.encode("utf-8"),
        str(bucket).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    # Keep the key short enough to read over voice/chat.
    return digest[:12].upper()


def current_api_key(now_utc: datetime | None = None) -> str:
    current = now_utc or datetime.now(timezone.utc)
    bucket = int(current.timestamp() // settings.api_key_period_seconds)
    return _api_key_for_bucket(bucket)


def verify_api_key(value: str, now_utc: datetime | None = None) -> bool:
    current = now_utc or datetime.now(timezone.utc)
    current_bucket = int(current.timestamp() // settings.api_key_period_seconds)

    for offset in range(settings.api_key_grace_periods + 1):
        for candidate_bucket in (current_bucket - offset, current_bucket + offset):
            if hmac.compare_digest(value.strip().upper(), _api_key_for_bucket(candidate_bucket)):
                return True

    return False


def hash_device_key(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_device_key() -> str:
    return secrets.token_urlsafe(32)


def create_access_token(user_id: int) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def parse_access_token(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except JWTError:
        return None

    sub = payload.get("sub")
    if not sub or not str(sub).isdigit():
        return None

    return int(sub)


def create_admin_session() -> str:
    serializer = URLSafeSerializer(settings.jwt_secret, salt="admin-session")
    return serializer.dumps({"role": "admin"})


def verify_admin_session(token: str) -> bool:
    serializer = URLSafeSerializer(settings.jwt_secret, salt="admin-session")
    try:
        data = serializer.loads(token)
    except BadSignature:
        return False

    return data.get("role") == "admin"
