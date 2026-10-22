import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    PROJECT_NAME: str = "Certificate Generator"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'certificates.db'}"
    
    # Storage paths
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    TEMPLATES_DIR: Path = BASE_DIR / "uploads" / "templates"
    GENERATED_DIR: Path = BASE_DIR / "uploads" / "generated"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # File limits
    MAX_FILE_SIZE_MB: int = 25
    ALLOWED_EXTENSIONS: list[str] = [".pdf", ".png", ".jpg", ".jpeg"]
    
    # Google Sheets credentials (optional fallback to public CSV or direct upload)
    GOOGLE_API_KEY: str = ""
    GOOGLE_SERVICE_ACCOUNT_FILE: str = ""
    GOOGLE_SERVICE_ACCOUNT_JSON: str = ""
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"]

    # Firebase Configuration
    USE_FIREBASE: bool = True
    FIREBASE_KEY_PATH: str = str(BASE_DIR / "firebase-key.json")
    FIREBASE_KEY_JSON: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""
    FIREBASE_PROJECT_ID: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

settings = Settings()

# Ensure critical directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
settings.GENERATED_DIR.mkdir(parents=True, exist_ok=True)
