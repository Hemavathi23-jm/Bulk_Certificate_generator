import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import BASE_URL
from app.database import get_db
from app.models import Certificate, CertificateStatus
from app.schemas import CertificateResponse

router = APIRouter(prefix="/api/certificates", tags=["Certificates"])

@router.get("/{certificate_id}", response_model=CertificateResponse, summary="Get Certificate Details")
def get_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Retrieves metadata and generation status for a specific certificate.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found."
        )

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

@router.get("/{certificate_id}/download", summary="Download Single Certificate PDF")
def download_certificate(certificate_id: str, db: Session = Depends(get_db)):
    """
    Downloads the generated PDF certificate file for a recipient.
    """
    cert = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not cert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certificate with ID '{certificate_id}' not found."
        )

    if cert.status == CertificateStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Certificate generation is still pending or processing."
        )

    if cert.status == CertificateStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificate generation failed: {cert.error_message}"
        )

    if not cert.file_path or not os.path.exists(cert.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate file is missing from storage."
        )

    return FileResponse(
        path=cert.file_path,
        filename=cert.file_name or f"certificate_{cert.id}.pdf",
        media_type="application/pdf"
    )
