from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import Base, engine
from .routers import admin, auth, item_types, items, rooms

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "status": "ok",
        "docs": "/docs",
        "admin": "/admin",
    }


app.include_router(auth.router, prefix="/api")
app.include_router(rooms.router, prefix="/api")
app.include_router(item_types.router, prefix="/api")
app.include_router(items.router, prefix="/api")
app.include_router(admin.router)
