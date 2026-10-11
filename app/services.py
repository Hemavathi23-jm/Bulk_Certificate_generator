import os
import re
import uuid
import zipfile
import logging
from pathlib import Path
from datetime import datetime, timezone
import io
import csv
import openpyxl
from typing import Tuple, Optional, Dict, Any, List

from sqlalchemy.orm import Session
from app.config import STORAGE_DIR
from app.database import SessionLocal
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.schemas import CreateJobRequest, RecipientLooseInput
from app.generator import generate_pdf_certificate

logger = logging.getLogger(__name__)

NAME_COLUMN_ALIASES = {"name", "recipient_name", "full_name", "fullname", "student_name", "participant_name"}
EMAIL_COLUMN_ALIASES = {"email", "recipient_email", "email_address", "mail"}
ID_COLUMN_ALIASES = {"recipient_id", "id", "student_id", "roll_no", "roll_number", "emp_id"}

def parse_recipients_from_file(file_bytes: bytes, filename: str) -> List[RecipientLooseInput]:
    """
    Parses recipient records from an uploaded CSV or Excel (.xlsx) file.
    Automatically detects column headers for name, email, and ID,
    and maps any extra columns to custom_attributes.
    """
    filename_lower = filename.lower()
    records: List[Dict[str, Any]] = []

    if filename_lower.endswith(".csv"):
        # Decode CSV with utf-8-sig to handle Excel BOM
        content = None
        for encoding in ["utf-8-sig", "utf-8", "latin-1"]:
            try:
                content = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            raise ValueError("Unable to decode CSV file with supported encodings.")

        reader = csv.DictReader(io.StringIO(content))
        for row in reader:
            if any(val.strip() for val in row.values() if val):
                records.append(row)

    elif filename_lower.endswith(".xlsx") or filename_lower.endswith(".xls"):
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return []

        header = [str(col).strip() if col is not None else "" for col in rows[0]]
        for row_vals in rows[1:]:
            if not any(v is not None and str(v).strip() for v in row_vals):
                continue
            row_dict = {}
            for col_idx, col_name in enumerate(header):
                if col_name and col_idx < len(row_vals):
                    row_dict[col_name] = row_vals[col_idx]
            records.append(row_dict)
    else:
        raise ValueError(f"Unsupported file format '{filename}'. Please upload a CSV (.csv) or Excel (.xlsx) file.")

    if not records:
        raise ValueError("The uploaded file does not contain any recipient rows.")

    parsed_recipients: List[RecipientLooseInput] = []

    for row in records:
        clean_row = {str(k).strip().lower(): v for k, v in row.items() if k is not None}

        # 1. Detect Name
        name_val = None
        for key in NAME_COLUMN_ALIASES:
            if key in clean_row and clean_row[key] is not None:
                name_val = str(clean_row[key]).strip()
                break

        # 2. Detect Email
        email_val = None
        for key in EMAIL_COLUMN_ALIASES:
            if key in clean_row and clean_row[key] is not None:
                email_val = str(clean_row[key]).strip()
                break

        # 3. Detect Recipient ID
        rec_id_val = None
        for key in ID_COLUMN_ALIASES:
            if key in clean_row and clean_row[key] is not None:
                rec_id_val = str(clean_row[key]).strip()
                break

        # 4. Extra columns as custom attributes
        custom_attrs = {}
        for original_k, v in row.items():
            if original_k is None:
                continue
            norm_k = str(original_k).strip().lower()
            if norm_k not in NAME_COLUMN_ALIASES and norm_k not in EMAIL_COLUMN_ALIASES and norm_k not in ID_COLUMN_ALIASES:
                if v is not None and str(v).strip():
                    custom_attrs[str(original_k).strip()] = str(v).strip()

        parsed_recipients.append(
            RecipientLooseInput(
                name=name_val if name_val is not None else "",
                email=email_val if email_val is not None else "",
                recipient_id=rec_id_val,
                custom_attributes=custom_attrs if custom_attrs else None
            )
        )

    return parsed_recipients


logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$")

def validate_recipient_data(data: Any) -> Tuple[bool, Optional[str], str, str, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates recipient information.
    Returns:
        (is_valid, error_reason, clean_name, clean_email, recipient_id, custom_attributes)
    """
    if not isinstance(data, dict):
        try:
            data = data.model_dump()
        except Exception:
            return False, "Recipient record must be a valid key-value object.", "", "", None, None

    raw_name = data.get("name")
    raw_email = data.get("email")
    recipient_id = data.get("recipient_id")
    custom_attributes = data.get("custom_attributes") or {}

    # Validate Name
    if raw_name is None:
        return False, "Recipient name is missing.", "", "", None, None
    clean_name = str(raw_name).strip()
    if not clean_name:
        return False, "Recipient name cannot be empty or whitespace.", "", "", None, None
    if len(clean_name) > 255:
        return False, "Recipient name exceeds maximum allowed length of 255 characters.", "", "", None, None

    # Validate Email
    if raw_email is None:
        return False, "Recipient email is missing.", clean_name, "", None, None
    clean_email = str(raw_email).strip()
    if not clean_email or not EMAIL_REGEX.match(clean_email):
        return False, f"Invalid email format: '{clean_email}'. Must be a valid email (e.g. user@domain.com).", clean_name, clean_email, None, None

    # Clean Recipient ID
    clean_rec_id = str(recipient_id).strip() if recipient_id is not None else None

    return True, None, clean_name, clean_email, clean_rec_id, custom_attributes


def create_bulk_job(db: Session, request: CreateJobRequest) -> Job:
    """
    Creates a new bulk certificate generation job and pre-registers certificates.
    """
    job_id = str(uuid.uuid4())
    issue_date = request.issue_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    cert_title = request.certificate_title or "Certificate of Achievement"

    job = Job(
        id=job_id,
        event_name=request.event_name.strip(),
        issuer_name=request.issuer_name.strip(),
        issue_date=issue_date.strip(),
        certificate_title=cert_title.strip(),
        status=JobStatus.PENDING.value,
        total_count=len(request.recipients),
        success_count=0,
        failed_count=0,
        created_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.flush()

    for item in request.recipients:
        cert_id = str(uuid.uuid4())
        raw_dict = item.model_dump() if hasattr(item, "model_dump") else dict(item)

        raw_name = str(raw_dict.get("name") or "Unknown")
        raw_email = str(raw_dict.get("email") or "unknown@domain.com")
        rec_id = str(raw_dict.get("recipient_id")) if raw_dict.get("recipient_id") else None
        custom_attrs = raw_dict.get("custom_attributes")

        certificate = Certificate(
            id=cert_id,
            job_id=job.id,
            recipient_name=raw_name,
            recipient_email=raw_email,
            recipient_id=rec_id,
            custom_attributes=custom_attrs,
            status=CertificateStatus.PENDING.value,
            created_at=datetime.now(timezone.utc)
        )
        db.add(certificate)

    db.commit()
    db.refresh(job)
    return job


def process_certificate_job(job_id: str):
    """
    Background worker that iterates through all recipients in a job,
    validates data, generates PDF certificates, and isolates failures.
    """
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error("Job %s not found in background processor.", job_id)
            return

        job.status = JobStatus.PROCESSING.value
        db.commit()

        job_dir = STORAGE_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)

        certificates = db.query(Certificate).filter(Certificate.job_id == job.id).all()

        for cert in certificates:
            # Skip if already processed
            if cert.status != CertificateStatus.PENDING.value:
                continue

            # 1. Validate recipient data
            is_valid, err_reason, clean_name, clean_email, rec_id, custom_attrs = validate_recipient_data({
                "name": cert.recipient_name,
                "email": cert.recipient_email,
                "recipient_id": cert.recipient_id,
                "custom_attributes": cert.custom_attributes
            })

            if not is_valid:
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = f"Validation Error: {err_reason}"
                db.commit()
                continue

            # Update cleaned info
            cert.recipient_name = clean_name
            cert.recipient_email = clean_email
            cert.recipient_id = rec_id

            # 2. Generate PDF Certificate
            # Safe sanitized file name
            safe_name = "".join(c for c in clean_name if c.isalnum() or c in (" ", "_", "-")).rstrip().replace(" ", "_")
            file_name = f"cert_{safe_name}_{cert.id[:8]}.pdf"
            file_path = job_dir / file_name

            try:
                generate_pdf_certificate(
                    output_path=file_path,
                    recipient_name=clean_name,
                    event_name=job.event_name,
                    issuer_name=job.issuer_name,
                    issue_date=job.issue_date,
                    certificate_title=job.certificate_title,
                    certificate_id=cert.id,
                    custom_attributes=custom_attrs
                )

                cert.status = CertificateStatus.SUCCESS.value
                cert.file_name = file_name
                cert.file_path = str(file_path)
                cert.error_message = None

            except Exception as ex:
                logger.exception("Failed to generate certificate for %s in job %s", clean_name, job.id)
                cert.status = CertificateStatus.FAILED.value
                cert.error_message = f"Generation Error: {str(ex)}"

            db.commit()

        # Update final job counts and state
        job.success_count = db.query(Certificate).filter(
            Certificate.job_id == job.id, Certificate.status == CertificateStatus.SUCCESS.value
        ).count()
        job.failed_count = db.query(Certificate).filter(
            Certificate.job_id == job.id, Certificate.status == CertificateStatus.FAILED.value
        ).count()

        job.completed_at = datetime.now(timezone.utc)
        if job.failed_count == 0 and job.success_count > 0:
            job.status = JobStatus.COMPLETED.value
        elif job.success_count > 0:
            job.status = JobStatus.PARTIAL_SUCCESS.value
        else:
            job.status = JobStatus.FAILED.value

        db.commit()
        logger.info("Job %s completed: %d success, %d failed", job.id, job.success_count, job.failed_count)

    except Exception as ex:
        logger.exception("Fatal failure in background processing for job %s: %s", job_id, str(ex))
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED.value
                job.error_message = f"Fatal Worker Failure: {str(ex)}"
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def create_job_zip_archive(job: Job) -> Optional[Path]:
    """
    Creates a ZIP archive containing all successfully generated certificates for a job.
    """
    db = SessionLocal()
    try:
        certificates = db.query(Certificate).filter(
            Certificate.job_id == job.id,
            Certificate.status == CertificateStatus.SUCCESS.value
        ).all()

        if not certificates:
            return None

        job_dir = STORAGE_DIR / job.id
        job_dir.mkdir(parents=True, exist_ok=True)

        safe_event_name = "".join(c for c in job.event_name if c.isalnum() or c in (" ", "_", "-")).rstrip().replace(" ", "_")
        zip_path = job_dir / f"{safe_event_name}_Certificates_{job.id[:8]}.zip"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for cert in certificates:
                if cert.file_path and os.path.exists(cert.file_path):
                    zip_file.write(cert.file_path, arcname=cert.file_name)

        return zip_path
    finally:
        db.close()
