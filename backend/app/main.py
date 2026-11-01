import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.database import init_db
from app.api import api_router

# Initialize Database Schema on load
init_db()

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-Powered Global Import-Export Buyer Acquisition & Automation System API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Core API Routes
app.include_router(api_router)

# Mount static frontend build if present (for single-container/single-server 1-click deployments)
# Checks both relative paths: from backend directory or from repository root
possible_static_paths = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "out")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend", "out")),
    os.path.abspath(os.path.join(os.getcwd(), "out")),
]

static_dir = next((p for p in possible_static_paths if os.path.isdir(p)), None)

if static_dir:
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    def root():
        return {
            "message": f"Welcome to {settings.APP_NAME}",
            "documentation": "/docs",
            "health": "/api/v1/health",
            "status": "operational"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)


