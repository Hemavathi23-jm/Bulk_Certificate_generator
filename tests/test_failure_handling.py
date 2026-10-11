import pytest
from app.services import process_certificate_job

def test_individual_certificate_failure_isolation(client):
    """
    Test that an invalid recipient failure does not prevent valid certificates
    in the same batch from being generated, yielding PARTIAL_SUCCESS.
    """
    payload = {
        "event_name": "Cloud Computing Summit",
        "issuer_name": "Cloud Academy",
        "recipients": [
            {
                "name": "Valid Recipient",
                "email": "valid.person@example.com"
            },
            {
                "name": "Invalid Email Person",
                "email": "not-an-email"  # Invalid email format
            },
            {
                "name": "   ",  # Blank name
                "email": "blank.name@example.com"
            }
        ]
    }

    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Process job
    process_certificate_job(job_id)

    # Check resulting job status
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    data = status_resp.json()

    assert data["status"] == "PARTIAL_SUCCESS"
    assert data["total_count"] == 3
    assert data["success_count"] == 1
    assert data["failed_count"] == 2

    # Verify per-certificate outcomes
    certs = {c["recipient_email"]: c for c in data["certificates"]}

    valid_cert = certs["valid.person@example.com"]
    assert valid_cert["status"] == "SUCCESS"
    assert valid_cert["download_url"] is not None
    assert valid_cert["error_message"] is None

    invalid_email_cert = certs["not-an-email"]
    assert invalid_email_cert["status"] == "FAILED"
    assert "Invalid email format" in invalid_email_cert["error_message"]
    assert invalid_email_cert["download_url"] is None
