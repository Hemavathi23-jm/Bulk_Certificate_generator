import pytest

def test_create_job_missing_required_fields(client):
    """Test creating a job without event_name or issuer_name fails with 422."""
    payload = {
        "event_name": "",
        "issuer_name": "Tech Corp",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}]
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422

    payload2 = {
        "event_name": "Valid Event",
        "issuer_name": "   ",
        "recipients": [{"name": "Alice", "email": "alice@example.com"}]
    }
    response2 = client.post("/api/jobs", json=payload2)
    assert response2.status_code == 422

def test_create_job_empty_recipients_list(client):
    """Test creating a job with empty recipients list fails with 422."""
    payload = {
        "event_name": "Python Bootcamp",
        "issuer_name": "PyOrg",
        "recipients": []
    }
    response = client.post("/api/jobs", json=payload)
    assert response.status_code == 422

def test_recipient_validation_rules():
    """Test unit validation function for recipient records."""
    from app.services import validate_recipient_data

    # Valid recipient
    valid, err, name, email, rec_id, custom = validate_recipient_data({
        "name": "Jane Doe",
        "email": "jane.doe@example.com",
        "recipient_id": "REC-01"
    })
    assert valid is True
    assert err is None
    assert name == "Jane Doe"
    assert email == "jane.doe@example.com"

    # Missing name
    valid, err, _, _, _, _ = validate_recipient_data({
        "name": "   ",
        "email": "user@domain.com"
    })
    assert valid is False
    assert "name cannot be empty" in err

    # Invalid email
    valid, err, _, _, _, _ = validate_recipient_data({
        "name": "Bob Smith",
        "email": "invalid-email-address"
    })
    assert valid is False
    assert "Invalid email format" in err
