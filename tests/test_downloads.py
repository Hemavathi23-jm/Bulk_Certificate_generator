import io
import zipfile
import pytest
from app.services import process_certificate_job

def test_download_single_certificate(client):
    """Test retrieving and downloading a single generated certificate PDF."""
    payload = {
        "event_name": "AI Workshop",
        "issuer_name": "AI Institute",
        "recipients": [{"name": "Bruce Wayne", "email": "bruce@wayne.com"}]
    }

    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["id"]

    process_certificate_job(job_id)

    status_resp = client.get(f"/api/jobs/{job_id}")
    cert_id = status_resp.json()["certificates"][0]["id"]

    # 1. Get certificate details
    detail_resp = client.get(f"/api/certificates/{cert_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["recipient_name"] == "Bruce Wayne"

    # 2. Download certificate PDF
    dl_resp = client.get(f"/api/certificates/{cert_id}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.headers["content-type"] == "application/pdf"
    # PDF magic bytes %PDF
    assert dl_resp.content.startswith(b"%PDF")

def test_download_all_certificates_zip(client):
    """Test downloading all certificates for a job as a ZIP file."""
    payload = {
        "event_name": "Security Symposium",
        "issuer_name": "CyberSec Org",
        "recipients": [
            {"name": "Diana Prince", "email": "diana@themyscira.com"},
            {"name": "Clark Kent", "email": "clark@dailyplanet.com"}
        ]
    }

    create_resp = client.post("/api/jobs", json=payload)
    job_id = create_resp.json()["id"]

    process_certificate_job(job_id)

    # Download ZIP
    zip_resp = client.get(f"/api/jobs/{job_id}/download-all")
    assert zip_resp.status_code == 200
    assert zip_resp.headers["content-type"] == "application/zip"

    # Verify ZIP contains 2 PDF files
    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
        file_list = zf.namelist()
        assert len(file_list) == 2
        for name in file_list:
            assert name.endswith(".pdf")

def test_download_nonexistent_certificate(client):
    """Test 404 error when downloading non-existent certificate."""
    response = client.get("/api/certificates/nonexistent-id/download")
    assert response.status_code == 404
