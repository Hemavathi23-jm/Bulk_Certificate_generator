import time
import pytest
from app.services import process_certificate_job

def test_create_and_process_job(client):
    """Test full cycle of creating a job and processing certificate generation."""
    payload = {
        "event_name": "Full Stack Workshop",
        "issuer_name": "Global Tech Institute",
        "issue_date": "2026-10-15",
        "certificate_title": "Certificate of Excellence",
        "recipients": [
            {
                "name": "Sarah Connor",
                "email": "sarah.connor@example.com",
                "recipient_id": "REC-101",
                "custom_attributes": {"Grade": "A+", "Track": "Advanced"}
            },
            {
                "name": "John Connor",
                "email": "john.connor@example.com",
                "recipient_id": "REC-102"
            }
        ]
    }

    # 1. Create Job
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    data = response.json()
    job_id = data["id"]
    assert data["total_count"] == 2
    assert len(data["certificates"]) == 2

    # 2. Process job explicitly to test background worker logic
    process_certificate_job(job_id)

    # 3. Check Job Status
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()

    assert status_data["status"] == "COMPLETED"
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 0
    assert status_data["progress_percentage"] == 100.0
    assert status_data["download_all_url"] is not None

    # Check certificate details
    for cert in status_data["certificates"]:
        assert cert["status"] == "SUCCESS"
        assert cert["download_url"] is not None
        assert cert["file_name"].endswith(".pdf")

def test_list_jobs(client):
    """Test listing jobs endpoint."""
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
