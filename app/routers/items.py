from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..deps import get_current_user, get_db
from ..models import Item, ItemLocationHistory, Room, User
from ..schemas import ItemCreate, ItemHistoryEntry, ItemOut, ItemUpdate, MoveItemRequest

router = APIRouter(prefix="/items", tags=["items"])


def _ensure_room_exists(db: Session, room_id: int | None) -> None:
    if room_id is None:
        return

    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")


def _add_history(
    db: Session,
    item: Item,
    from_room_id: int | None,
    to_room_id: int | None,
    moved_by_user_id: int,
    comment: str | None,
) -> None:
    history = ItemLocationHistory(
        item_id=item.id,
        inventory_number=item.inventory_number,
        from_room_id=from_room_id,
        to_room_id=to_room_id,
        moved_by_user_id=moved_by_user_id,
        comment=comment,
    )
    db.add(history)


@router.get("", response_model=list[ItemOut])
def list_items(
    query: str | None = Query(default=None),
    item_type: str | None = Query(default=None),
    room_id: int | None = Query(default=None),
    attached: bool | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItemOut]:
    stmt = db.query(Item).options(joinedload(Item.default_room))

    if query:
        pattern = f"%{query.strip()}%"
        stmt = stmt.filter(
            or_(
                Item.inventory_number.ilike(pattern),
                Item.item_name.ilike(pattern),
            )
        )

    if item_type:
        stmt = stmt.filter(Item.item_type == item_type)

    if room_id is not None:
        stmt = stmt.filter(Item.default_room_id == room_id)

    if attached is True:
        stmt = stmt.filter(Item.default_room_id.isnot(None))
    elif attached is False:
        stmt = stmt.filter(Item.default_room_id.is_(None))

    return stmt.order_by(Item.updated_at.desc()).all()


@router.post("", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def create_item(
    payload: ItemCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemOut:
    duplicate = db.query(Item.id).filter(Item.inventory_number == payload.inventory_number).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Inventory number already exists")

    _ensure_room_exists(db, payload.default_room_id)

    item = Item(
        inventory_number=payload.inventory_number,
        item_type=payload.item_type,
        item_name=payload.item_name,
        properties_json=payload.properties_json,
        default_room_id=payload.default_room_id,
    )
    db.add(item)
    db.flush()

    if payload.default_room_id is not None:
        _add_history(
            db=db,
            item=item,
            from_room_id=None,
            to_room_id=payload.default_room_id,
            moved_by_user_id=user.id,
            comment="initial placement",
        )

    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemOut)
def get_item(
    item_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemOut:
    item = db.query(Item).options(joinedload(Item.default_room)).filter(Item.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    return item


@router.put("/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemOut:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    old_room_id = item.default_room_id
    updates = payload.model_dump(exclude_unset=True)
    room_changed = False
    new_room_id = old_room_id

    if "default_room_id" in updates:
        new_room_id = updates["default_room_id"]
        _ensure_room_exists(db, new_room_id)
        room_changed = new_room_id != old_room_id

    for key, value in updates.items():
        setattr(item, key, value)

    if room_changed:
        _add_history(
            db=db,
            item=item,
            from_room_id=old_room_id,
            to_room_id=new_room_id,
            moved_by_user_id=user.id,
            comment="room changed from item update",
        )

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    db.delete(item)
    db.commit()
    return None


@router.post("/{item_id}/move", response_model=ItemOut)
def move_item(
    item_id: int,
    payload: MoveItemRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemOut:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    _ensure_room_exists(db, payload.to_room_id)

    old_room_id = item.default_room_id
    if old_room_id == payload.to_room_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Item is already in this room")

    item.default_room_id = payload.to_room_id
    _add_history(
        db=db,
        item=item,
        from_room_id=old_room_id,
        to_room_id=payload.to_room_id,
        moved_by_user_id=user.id,
        comment=payload.comment,
    )

    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}/history", response_model=list[ItemHistoryEntry])
def item_history(
    item_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItemHistoryEntry]:
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    records = (
        db.query(ItemLocationHistory)
        .options(
            joinedload(ItemLocationHistory.from_room),
            joinedload(ItemLocationHistory.to_room),
            joinedload(ItemLocationHistory.moved_by_user),
        )
        .filter(ItemLocationHistory.item_id == item_id)
        .order_by(ItemLocationHistory.moved_at.desc())
        .all()
    )

    return [
        ItemHistoryEntry(
            id=record.id,
            item_id=record.item_id,
            inventory_number=record.inventory_number,
            from_room_id=record.from_room_id,
            from_room_number=record.from_room.number if record.from_room else None,
            to_room_id=record.to_room_id,
            to_room_number=record.to_room.number if record.to_room else None,
            moved_by_user_id=record.moved_by_user_id,
            moved_by_username=record.moved_by_user.username if record.moved_by_user else None,
            moved_at=record.moved_at,
            comment=record.comment,
        )
        for record in records
    ]
