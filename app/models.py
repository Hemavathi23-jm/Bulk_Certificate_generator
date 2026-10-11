import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"

class CertificateStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

def get_utc_now():
    return datetime.now(timezone.utc)

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, index=True)
    event_name = Column(String(255), nullable=False)
    issuer_name = Column(String(255), nullable=False)
    issue_date = Column(String(50), nullable=False)
    certificate_title = Column(String(255), nullable=False, default="Certificate of Achievement")
    status = Column(String(50), nullable=False, default=JobStatus.PENDING.value, index=True)
    total_count = Column(Integer, nullable=False, default=0)
    success_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    certificates = relationship("Certificate", back_populates="job", cascade="all, delete-orphan", order_by="Certificate.created_at")

class Certificate(Base):
    __tablename__ = "certificates"

    id = Column(String(36), primary_key=True, index=True)
    job_id = Column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=False)
    recipient_email = Column(String(255), nullable=False)
    recipient_id = Column(String(100), nullable=True)
    custom_attributes = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default=CertificateStatus.PENDING.value, index=True)
    file_path = Column(String(500), nullable=True)
    file_name = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=get_utc_now)

    # Relationships
    job = relationship("Job", back_populates="certificates")
