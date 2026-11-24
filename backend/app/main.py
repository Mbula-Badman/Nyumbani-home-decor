from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, engine, get_db
from app.models import __all__  # ensure every SQLAlchemy model is registered
from app.routers import auth, catalog, checkout, dashboards
from app.uploads import UPLOADS_DIR
from seed import main as seed_database

app = FastAPI(title=settings.app_name)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(catalog.router)
app.include_router(checkout.router)
app.include_router(dashboards.router)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"


@app.on_event("startup")
def startup():
    if settings.app_env == "production" and not settings.auth_secret:
        raise RuntimeError("AUTH_SECRET must be configured in production.")
    Base.metadata.create_all(bind=engine)
    seed_database()


@app.get("/", include_in_schema=False)
def storefront():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health_check():
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}


@app.get("/api/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"database": "ok"}
