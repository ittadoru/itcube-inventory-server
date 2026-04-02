import random
import string
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_db, get_current_user
from ..models import User, UserDevice
from ..schemas import AuthByApiKeyRequest, AuthByDeviceRequest, AuthResponse, UserOut
from ..security import create_access_token, hash_device_key, verify_api_key

router = APIRouter(prefix="/auth", tags=["auth"])


LATIN = string.ascii_lowercase


def _generate_username(length: int = 8) -> str:
    return "".join(random.choice(LATIN) for _ in range(length))


def _create_unique_username(db: Session) -> str:
    for _ in range(50):
        candidate = _generate_username()
        exists = db.query(User.id).filter(User.username == candidate).first()
        if not exists:
            return candidate

    raise RuntimeError("Unable to generate unique username")


def _auth_response_for_user(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id),
        user_id=user.id,
        username=user.username,
    )


@router.post("/login-by-api-key", response_model=AuthResponse)
def login_by_api_key(payload: AuthByApiKeyRequest, db: Session = Depends(get_db)) -> AuthResponse:
    if not verify_api_key(payload.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API key")

    device_hash = hash_device_key(payload.device_key)
    device = db.query(UserDevice).filter(UserDevice.device_hash == device_hash).first()

    if device:
        user = db.get(User, device.user_id)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

        device.last_seen_at = datetime.utcnow()
        db.commit()
        return _auth_response_for_user(user)

    username = _create_unique_username(db)
    user = User(username=username, is_active=True)
    db.add(user)
    db.flush()

    new_device = UserDevice(user_id=user.id, device_hash=device_hash)
    db.add(new_device)
    db.commit()
    db.refresh(user)
    return _auth_response_for_user(user)


@router.post("/login-by-device", response_model=AuthResponse)
def login_by_device(payload: AuthByDeviceRequest, db: Session = Depends(get_db)) -> AuthResponse:
    device_hash = hash_device_key(payload.device_key)
    device = db.query(UserDevice).filter(UserDevice.device_hash == device_hash).first()

    if device is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown device")

    user = db.get(User, device.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

    device.last_seen_at = datetime.utcnow()
    db.commit()
    return _auth_response_for_user(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return user
