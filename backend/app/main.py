from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal, init_db
from .routers import attempts, exams, health, reports, runs, submissions
from .seed import seed_database

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(exams.router)
app.include_router(submissions.router)
app.include_router(runs.router)
app.include_router(attempts.router)
app.include_router(reports.router)


@app.on_event("startup")
def on_startup() -> None:
    if settings.auto_create_tables:
        init_db()

    if settings.auto_seed:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "running"}
