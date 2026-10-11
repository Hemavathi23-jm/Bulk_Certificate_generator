import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import init_db, get_db
from app.routers import jobs, certificates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("bulk_cert_generator")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables exist
    logger.info("Initializing database schema...")
    try:
        init_db()
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error("Database initialization warning: %s", str(e))
    yield
    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Bulk Certificate Generator API",
    description="A robust backend service for validating recipient lists, generating PDF certificates in bulk, tracking progress, and downloading certificates.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(jobs.router)
app.include_router(certificates.router)

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Bulk Certificate Generator API",
        "status": "online",
        "documentation": "/docs",
        "endpoints": {
            "submit_job": "POST /api/jobs",
            "get_job": "GET /api/jobs/{job_id}",
            "download_zip": "GET /api/jobs/{job_id}/download-all",
            "download_certificate": "GET /api/certificates/{certificate_id}/download"
        }
    }

@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
