import re
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import get_db, is_admin_authenticated
from ..models import User, UserDevice
from ..security import create_admin_session, current_api_key

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

USERNAME_RE = re.compile(r"^[A-Za-z]{3,32}$")


def _redirect_login() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def admin_login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request=request, name="admin_login.html", context={"error": None})


@router.post("/login", response_class=HTMLResponse)
def admin_login_submit(request: Request, password: str = Form(...)):
    if password != settings.admin_password:
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Неверный пароль"},
            status_code=401,
        )

    response = RedirectResponse(url="/admin", status_code=303)
    response.set_cookie("admin_session", create_admin_session(), httponly=True, samesite="strict")
    return response


@router.get("/logout")
def admin_logout() -> RedirectResponse:
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie("admin_session")
    return response


@router.get("", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    if not is_admin_authenticated(request):
        return _redirect_login()

    users = db.query(User).order_by(User.created_at.desc()).all()
    devices = db.query(UserDevice).order_by(UserDevice.last_seen_at.desc()).all()
    users_by_id = {user.id: user for user in users}

    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
        context={
            "api_key": current_api_key(),
            "users": users,
            "devices": devices,
            "users_by_id": users_by_id,
        },
    )


@router.post("/users/{user_id}/rename")
def rename_user(
    user_id: int,
    request: Request,
    username: str = Form(...),
    db: Session = Depends(get_db),
):
    if not is_admin_authenticated(request):
        return _redirect_login()

    if not USERNAME_RE.fullmatch(username):
        return RedirectResponse(url="/admin", status_code=303)

    user = db.get(User, user_id)
    if user is None:
        return RedirectResponse(url="/admin", status_code=303)

    duplicate = db.query(User.id).filter(User.username == username, User.id != user_id).first()
    if duplicate:
        return RedirectResponse(url="/admin", status_code=303)

    user.username = username
    db.commit()
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    if not is_admin_authenticated(request):
        return _redirect_login()

    user = db.get(User, user_id)
    if user:
        db.delete(user)
        db.commit()

    return RedirectResponse(url="/admin", status_code=303)
