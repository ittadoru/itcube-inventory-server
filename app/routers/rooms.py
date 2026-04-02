from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Item, Room, User
from ..schemas import RoomCreate, RoomOut, RoomUpdate

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomOut])
def list_rooms(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RoomOut]:
    return db.query(Room).order_by(Room.number.asc()).all()


@router.post("", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
def create_room(
    payload: RoomCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomOut:
    duplicate = db.query(Room.id).filter(Room.number == payload.number).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room with this number already exists")

    room = Room(name=payload.name, number=payload.number, description=payload.description)
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/{room_id}", response_model=RoomOut)
def update_room(
    room_id: int,
    payload: RoomUpdate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RoomOut:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    if payload.number and payload.number != room.number:
        duplicate = db.query(Room.id).filter(Room.number == payload.number).first()
        if duplicate:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room number already exists")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(room, key, value)

    db.commit()
    db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(
    room_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    db.query(Item).filter(Item.default_room_id == room_id).update({Item.default_room_id: None})
    db.delete(room)
    db.commit()
    return None
