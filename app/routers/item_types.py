from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..deps import get_current_user, get_db
from ..models import Item, ItemType, User
from ..schemas import ItemTypeCreate, ItemTypeOut

router = APIRouter(prefix="/item-types", tags=["item-types"])


@router.get("", response_model=list[ItemTypeOut])
def list_item_types(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ItemTypeOut]:
    return db.query(ItemType).order_by(ItemType.name.asc()).all()


@router.post("", response_model=ItemTypeOut, status_code=status.HTTP_201_CREATED)
def create_item_type(
    payload: ItemTypeCreate,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ItemTypeOut:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Type name is required")

    duplicate = db.query(ItemType.id).filter(ItemType.name == name).first()
    if duplicate:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Item type already exists")

    item_type = ItemType(name=name, description=payload.description)
    db.add(item_type)
    db.commit()
    db.refresh(item_type)
    return item_type


@router.delete("/{item_type_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item_type(
    item_type_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    item_type = db.get(ItemType, item_type_id)
    if item_type is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item type not found")

    in_use = db.query(Item.id).filter(Item.item_type == item_type.name).first()
    if in_use:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete type because it is used by items",
        )

    db.delete(item_type)
    db.commit()
    return None
