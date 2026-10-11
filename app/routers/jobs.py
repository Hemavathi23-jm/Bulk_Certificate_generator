import os
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_URL
from app.database import get_db
from app.models import Job, Certificate, JobStatus, CertificateStatus
from app.schemas import CreateJobRequest, JobStatusResponse, CertificateResponse, JobListSummary
from app.services import create_bulk_job, process_certificate_job, create_job_zip_archive, parse_recipients_from_file

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])

def serialize_certificate(cert: Certificate) -> CertificateResponse:
    download_url = None
    if cert.status == CertificateStatus.SUCCESS.value and cert.file_path:
        download_url = f"{BASE_URL}/api/certificates/{cert.id}/download"

    return CertificateResponse(
        id=cert.id,
        job_id=cert.job_id,
        recipient_name=cert.recipient_name,
        recipient_email=cert.recipient_email,
        recipient_id=cert.recipient_id,
        custom_attributes=cert.custom_attributes,
        status=cert.status,
        file_name=cert.file_name,
        download_url=download_url,
        error_message=cert.error_message,
        created_at=cert.created_at
    )

def serialize_job(job: Job) -> JobStatusResponse:
    total = job.total_count or 1
    processed = job.success_count + job.failed_count
    progress = round((processed / total) * 100, 2) if total > 0 else 0.0

    download_all_url = None
    if job.status in [JobStatus.COMPLETED.value, JobStatus.PARTIAL_SUCCESS.value] and job.success_count > 0:
        download_all_url = f"{BASE_URL}/api/jobs/{job.id}/download-all"

    return JobStatusResponse(
        id=job.id,
        event_name=job.event_name,
        issuer_name=job.issuer_name,
        issue_date=job.issue_date,
        certificate_title=job.certificate_title,
        status=job.status,
        total_count=job.total_count,
        success_count=job.success_count,
        failed_count=job.failed_count,
        progress_percentage=progress,
        created_at=job.created_at,
        completed_at=job.completed_at,
        download_all_url=download_all_url,
        error_message=job.error_message,
        certificates=[serialize_certificate(c) for c in job.certificates]
    )

@router.post("", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED, summary="Submit Bulk Certificate Request")
def submit_certificate_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Submits a bulk certificate generation request for multiple recipients.
    Processes generation asynchronously in the background and returns job tracking details.
    """
    job = create_bulk_job(db, request)
    background_tasks.add_task(process_certificate_job, job.id)
    return serialize_job(job)

@router.post("/upload-file", response_model=JobStatusResponse, status_code=status.HTTP_202_ACCEPTED, summary="Upload CSV or Excel (.xlsx) File for Bulk Generation")
async def upload_recipients_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV or Excel (.xlsx) file containing recipient rows"),
    event_name: str = Form(..., description="Event or course name"),
    issuer_name: str = Form(..., description="Organization or mentor issuing certificate"),
    issue_date: Optional[str] = Form(None, description="Date of issuance (YYYY-MM-DD)"),
    certificate_title: Optional[str] = Form("Certificate of Achievement", description="Certificate title"),
    db: Session = Depends(get_db)
):
    """
    Uploads a spreadsheet (CSV or Excel) containing recipients, parses rows,
    initiates the background certificate generation job, and returns tracking status.
    """
    clean_event = event_name.strip()
    clean_issuer = issuer_name.strip()
    if not clean_event or not clean_issuer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="event_name and issuer_name cannot be empty or whitespace."
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        recipients = parse_recipients_from_file(file_bytes, file.filename or "upload.csv")
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )

    job_request = CreateJobRequest(
        event_name=clean_event,
        issuer_name=clean_issuer,
        issue_date=issue_date.strip() if issue_date else None,
        certificate_title=certificate_title.strip() if certificate_title else "Certificate of Achievement",
        recipients=recipients
    )

    job = create_bulk_job(db, job_request)
    background_tasks.add_task(process_certificate_job, job.id)
    return serialize_job(job)

@router.get("/{job_id}", response_model=JobStatusResponse, summary="Get Job Status and Certificates")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the status, progress, recipient outcomes, and download links for a specific job.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )
    return serialize_job(job)

@router.get("/{job_id}/download-all", summary="Download All Certificates as ZIP")
def download_all_certificates(job_id: str, db: Session = Depends(get_db)):
    """
    Downloads all successfully generated certificates in this job bundled inside a single ZIP file.
    """
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found."
        )

    if job.status == JobStatus.PENDING.value or job.status == JobStatus.PROCESSING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job is still processing. Please wait until generation is completed."
        )

    if job.success_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certificates were successfully generated for this job."
        )

    zip_path = create_job_zip_archive(job)
    if not zip_path or not zip_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bundle certificates into a ZIP archive."
        )

    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip"
    )

@router.get("", response_model=List[JobListSummary], summary="List Generation Jobs")
def list_jobs(
    skip: int = Query(0, ge=0, description="Offset"),
    limit: int = Query(20, ge=1, le=100, description="Page size"),
    db: Session = Depends(get_db)
):
    """
    Returns a paginated list of all certificate generation jobs.
    """
    jobs = db.query(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit).all()
    return jobs
