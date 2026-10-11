import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from urllib.parse import urlparse
from app.config import DATABASE_URL, DB_NAME

logger = logging.getLogger(__name__)

Base = declarative_base()

def create_db_if_not_exists():
    """Ensure MySQL database exists before attempting to connect to it."""
    if DATABASE_URL.startswith("mysql"):
        try:
            # Parse database name and server connection string
            # Connect to server root without database name to run CREATE DATABASE
            prefix, slash, db = DATABASE_URL.rpartition("/")
            server_url = f"{prefix}/"
            root_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
            with root_engine.connect() as conn:
                conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            root_engine.dispose()
            logger.info("Database '%s' ensured in MySQL.", DB_NAME)
        except Exception as e:
            logger.warning("Could not auto-create database '%s': %s", DB_NAME, str(e))

create_db_if_not_exists()

# Create main SQLAlchemy engine
engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 3600
    })

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
