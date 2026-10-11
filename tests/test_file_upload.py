import io
import openpyxl
import pytest

def test_upload_csv_bulk_generation(client):
    """Test bulk certificate job creation via CSV file upload."""
    csv_content = """name,email,recipient_id,Grade
Peter Parker,peter.parker@dailybugle.com,P-101,A+
Miles Morales,miles.morales@brooklyn.edu,P-102,A
Invalid Person,bad-email,P-103,B
"""
    files = {
        "file": ("students.csv", csv_content.encode("utf-8"), "text/csv")
    }
    data = {
        "event_name": "Web Slinging 101",
        "issuer_name": "Spider Academy",
        "certificate_title": "Certificate of Mastery"
    }

    response = client.post("/api/jobs/upload-file", files=files, data=data)
    assert response.status_code == 202
    resp_data = response.json()
    job_id = resp_data["id"]
    assert resp_data["total_count"] == 3

    # Check job status
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "PARTIAL_SUCCESS"
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 1

def test_upload_excel_bulk_generation(client):
    """Test bulk certificate job creation via Excel (.xlsx) file upload."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Full Name", "Email Address", "Student ID", "Track"])
    ws.append(["Tony Stark", "tony@starkindustries.com", "S-001", "Robotics"])
    ws.append(["Pepper Potts", "pepper@starkindustries.com", "S-002", "Operations"])

    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)

    files = {
        "file": ("participants.xlsx", excel_buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    }
    data = {
        "event_name": "Arc Reactor Engineering",
        "issuer_name": "Stark Labs"
    }

    response = client.post("/api/jobs/upload-file", files=files, data=data)
    assert response.status_code == 202
    job_id = response.json()["id"]

    # Check job status
    status_resp = client.get(f"/api/jobs/{job_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "COMPLETED"
    assert status_data["success_count"] == 2
    assert status_data["failed_count"] == 0

def test_upload_invalid_file_extension(client):
    """Test error when uploading non-csv, non-xlsx file."""
    files = {
        "file": ("notes.txt", b"plain text", "text/plain")
    }
    data = {
        "event_name": "Test Event",
        "issuer_name": "Test Issuer"
    }
    response = client.post("/api/jobs/upload-file", files=files, data=data)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]
