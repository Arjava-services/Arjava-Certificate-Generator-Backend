import os
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.config.settings import settings
from app.models.database import Base, engine
from app.api.v1 import api_v1_router

from sqlalchemy import text

# Initialize database tables
Base.metadata.create_all(bind=engine)

# Auto-migrate any newly added columns in SQLite
try:
    with engine.connect() as conn:
        for col, col_def in [
            ("is_italic", "BOOLEAN DEFAULT 0"),
            ("opacity", "FLOAT DEFAULT 1.0"),
            ("text_case", "VARCHAR(16) DEFAULT 'none'"),
            ("letter_spacing", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE project_field_mappings ADD COLUMN {col} {col_def}"))
                conn.commit()
            except Exception:
                pass
except Exception:
    pass

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Automated Certificate Generator for bulk personalized certificates from Google Sheets",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Friendly custom exception handler to avoid leaking raw traces
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"An error occurred while processing your request: {str(exc)}"}
    )

# Include API v1 router
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

@app.get("/api/health", tags=["health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True)
