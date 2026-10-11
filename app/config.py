import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "bulk_cert_db")

# Constructed or overridden Database URL
DEFAULT_MYSQL_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_MYSQL_URL)

# Storage configuration
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", BASE_DIR / "generated_certificates"))
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Base URL for API links
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
