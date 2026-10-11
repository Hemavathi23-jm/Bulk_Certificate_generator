import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator

from pydantic import BaseModel, Field, field_validator, ConfigDict

EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")

class RecipientInput(BaseModel):
    name: str = Field(..., description="Full name of the recipient", examples=["John Doe"])
    email: str = Field(..., description="Valid email address of the recipient", examples=["john.doe@example.com"])
    recipient_id: Optional[str] = Field(None, description="Optional recipient identifier", examples=["REC-1001"])
    custom_attributes: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Arbitrary additional recipient metadata")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Recipient name cannot be empty or whitespace only.")
        return clean

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip()
        if not EMAIL_REGEX.match(clean):
            raise ValueError(f"Invalid email address format: '{v}'")
        return clean

class RecipientLooseInput(BaseModel):
    """Allows flexible recipient input so invalid recipients can be isolated instead of rejecting entire batch."""
    name: Any = Field(..., description="Recipient name")
    email: Any = Field(..., description="Recipient email")
    recipient_id: Optional[Any] = None
    custom_attributes: Optional[Dict[str, Any]] = None

class CreateJobRequest(BaseModel):
    event_name: str = Field(..., min_length=1, max_length=255, description="Name of event, course, or workshop", examples=["Full Stack Web Development"])
    issuer_name: str = Field(..., min_length=1, max_length=255, description="Name of issuing organization or mentor", examples=["Tech Institute"])
    issue_date: Optional[str] = Field(None, description="Date of certificate issuance (YYYY-MM-DD). Defaults to today.", examples=["2026-10-15"])
    certificate_title: Optional[str] = Field("Certificate of Achievement", description="Title displayed on certificate", examples=["Certificate of Completion"])
    recipients: List[RecipientLooseInput] = Field(..., min_length=1, description="List of recipient records to generate certificates for")

    @field_validator("event_name", "issuer_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Field cannot be empty or whitespace.")
        return clean

class CertificateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    recipient_name: str
    recipient_email: str
    recipient_id: Optional[str] = None
    custom_attributes: Optional[Dict[str, Any]] = None
    status: str
    file_name: Optional[str] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

class JobStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    issuer_name: str
    issue_date: str
    certificate_title: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None
    download_all_url: Optional[str] = None
    error_message: Optional[str] = None
    certificates: List[CertificateResponse] = []

class JobListSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_name: str
    issuer_name: str
    issue_date: str
    certificate_title: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    created_at: datetime
    completed_at: Optional[datetime] = None

