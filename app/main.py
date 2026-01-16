import os
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import SessionLocal
from app.routers import auth, home, learn, practice, review, admin, level_analysis

app = FastAPI(
    title="Coach Vocabulary API",
    description="API for vocabulary learning with spaced repetition",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files only if directory exists (not in Cloud Run with GCS)
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(home.router)
app.include_router(learn.router)
app.include_router(practice.router)
app.include_router(review.router)
app.include_router(admin.router)
app.include_router(level_analysis.router)


@app.get("/")
def root():
    return {"message": "Coach Vocabulary API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    current_time = datetime.utcnow().isoformat() + "Z"

    try:
        with SessionLocal() as session:
            # Get current migration version
            result = session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            migration_version = result.scalar()
            # Get word count
            result = session.execute(text("SELECT COUNT(*) FROM words"))
            word_count = result.scalar()
    except Exception:
        migration_version = "unknown"
        word_count = "unknown"

    return {
        "timestamp": current_time,
        "db_migration_version": migration_version,
        "word_count": word_count
    }
