from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuthByApiKeyRequest(BaseModel):
    api_key: str
    device_key: str


class AuthByDeviceRequest(BaseModel):
    device_key: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime
    is_active: bool


class UserRenameRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)


class RoomBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    number: str = Field(min_length=1, max_length=32)
    description: str | None = None


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    number: str | None = Field(default=None, min_length=1, max_length=32)
    description: str | None = None


class RoomOut(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ItemTypeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    description: str | None = None


class ItemTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class ItemBase(BaseModel):
    inventory_number: str = Field(min_length=1, max_length=128)
    item_type: str = Field(min_length=1, max_length=128)
    item_name: str = Field(min_length=1, max_length=256)
    properties_json: dict[str, Any] = Field(default_factory=dict)
    default_room_id: int | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    item_type: str | None = Field(default=None, min_length=1, max_length=128)
    item_name: str | None = Field(default=None, min_length=1, max_length=256)
    properties_json: dict[str, Any] | None = None
    default_room_id: int | None = None


class ItemOut(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    default_room: RoomOut | None = None


class MoveItemRequest(BaseModel):
    to_room_id: int | None = None
    comment: str | None = None


class ItemHistoryEntry(BaseModel):
    id: int
    item_id: int
    inventory_number: str
    from_room_id: int | None
    from_room_number: str | None
    to_room_id: int | None
    to_room_number: str | None
    moved_by_user_id: int | None
    moved_by_username: str | None
    moved_at: datetime
    comment: str | None
