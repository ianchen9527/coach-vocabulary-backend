from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
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

# Mount static files
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
    return {"status": "healthy"}
