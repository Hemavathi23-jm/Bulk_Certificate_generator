# Bulk Certificate Generator Backend

A high-performance, resilient backend API built with **Python**, **FastAPI**, **SQLAlchemy**, and **ReportLab** that accepts bulk certificate generation requests for hundreds of recipients, generates high-resolution PDF certificates using a predefined template, tracks generation progress, isolates recipient errors, and allows individual or bulk ZIP retrieval.

---

## Table of Contents
1. [Architecture & Features](#architecture--features)
2. [Tech Stack & Justification](#tech-stack--justification)
3. [Setup & Installation](#setup--installation)
4. [Running the Application](#running-the-application)
5. [Running Tests](#running-tests)
6. [API Endpoints & Usage Guide](#api-endpoints--usage-guide)
   - [1. Submit Bulk Certificate Job (`POST /api/jobs`)](#1-submit-bulk-certificate-job)
   - [2. Check Job Status & Progress (`GET /api/jobs/{job_id}`)](#2-check-job-status--progress)
   - [3. Download All Certificates as ZIP (`GET /api/jobs/{job_id}/download-all`)](#3-download-all-certificates-as-zip)
   - [4. Download Single Certificate PDF (`GET /api/certificates/{certificate_id}/download`)](#4-download-single-certificate-pdf)
   - [5. List All Jobs (`GET /api/jobs`)](#5-list-all-jobs)
7. [Important Design Decisions](#important-design-decisions)
   - [Bulk Processing & Background Tasks](#bulk-processing--background-tasks)
   - [Fault Isolation & Partial Success](#fault-isolation--partial-success)
   - [Vector PDF Generation with ReportLab](#vector-pdf-generation-with-reportlab)
   - [Database Choice & Portability](#database-choice--portability)
8. [Project Structure](#project-structure)

---

## Architecture & Features

* **Asynchronous Bulk Processing:** Accepts batches of recipients and immediately returns an HTTP `202 Accepted` response with a unique `job_id` and tracking URL, delegating CPU/IO work to background tasks.
* **Fault Isolation:** A single malformed recipient record (e.g., missing name or invalid email format) will **not** fail the job. Valid recipients continue to be generated, and the job status reflects `PARTIAL_SUCCESS` with actionable per-recipient error reasons.
* **Vector-Quality PDF Generation:** Generates landscape A4 certificates complete with outer double borders, golden corner accents, verification ID, issuance date, organization label, and authorized signature.
* **Progress Tracking:** Real-time polling endpoint providing `progress_percentage`, `success_count`, `failed_count`, and certificate download URLs.
* **Single & Bulk Downloads:** Direct download of individual PDF certificates and on-demand `.zip` archive bundling for downloading all generated certificates in a batch.
* **Self-Documenting API:** Interactive Swagger UI documentation accessible at `/docs` and ReDoc at `/redoc`.

---

## Tech Stack & Justification

| Layer | Component | Rationale |
| :--- | :--- | :--- |
| **Language** | Python 3.10+ | Clean syntax, robust standard library, excellent data processing and PDF generation ecosystem. |
| **Web Framework** | FastAPI | Async-first performance, automatic OpenAPI documentation, dependency injection, and native `BackgroundTasks`. |
| **Data Validation** | Pydantic (v2) | Schema enforcement, request validation, and clean serialization with type safety. |
| **ORM & Database** | SQLAlchemy & MySQL (with PyMySQL) | Relational database (ACID compliant, relational integrity between Jobs and Certificates, portable across MySQL, PostgreSQL, and SQLite). |
| **PDF Engine** | ReportLab | Native Python vector rendering. Creates crisp, printable, millimeter-accurate PDFs without external system dependencies like Chrome/wkhtmltopdf. |
| **Testing** | Pytest & HTTPX | Fast, isolated test suite covering unit validation, job workflows, failure isolation, and file downloads. |

---

## Setup & Installation

### Prerequisites
* Python 3.10+ installed
* MySQL server running (e.g. MySQL 8.0 on port 3306)

### 1. Clone or Navigate to Directory
```bash
cd d:/folders/Bulk_certificate_generator
```

### 2. Create and Activate Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and configure your MySQL credentials:
```ini
# Database Configuration (MySQL)
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=localhost
DB_PORT=3306
DB_NAME=bulk_cert_db

# Storage Directory for generated PDFs and ZIPs
STORAGE_DIR=generated_certificates
BASE_URL=http://localhost:8000
```
> **Note:** On first startup, the application connects to the MySQL server and automatically runs `CREATE DATABASE IF NOT EXISTS bulk_cert_db` and creates all required tables.

---

## Running the Application

Start the FastAPI server using Uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Once started:
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check Endpoint:** [http://localhost:8000/health](http://localhost:8000/health)

---

## Running Tests

The test suite runs with an isolated in-memory SQLite database using `StaticPool`, requiring zero setup or active database server.

Run pytest:
```bash
pytest -v
```

### What the test suite covers:
1. `tests/test_validation.py`: Input schema validation (empty strings, missing required fields, email format validation).
2. `tests/test_jobs.py`: Submitting bulk jobs, background generation execution, progress calculation, and job listing.
3. `tests/test_failure_handling.py`: Handling individual recipient failures in a batch without blocking valid recipients (`PARTIAL_SUCCESS` state).
4. `tests/test_downloads.py`: Single certificate PDF downloading and full-job ZIP bundle generation.

---

## API Endpoints & Usage Guide

### 1. Submit Bulk Certificate Job
Submits a list of recipients along with certificate and event information.

* **Endpoint:** `POST /api/jobs`
* **Status Code:** `202 Accepted`

#### Request Body
```json
{
  "event_name": "Full Stack Web Development Bootcamp",
  "issuer_name": "Tech Academy Global",
  "issue_date": "2026-10-15",
  "certificate_title": "Certificate of Completion",
  "recipients": [
    {
      "name": "Alice Johnson",
      "email": "alice.johnson@example.com",
      "recipient_id": "STU-001",
      "custom_attributes": {
        "Grade": "Distinction",
        "Track": "Backend Engineering"
      }
    },
    {
      "name": "Bob Smith",
      "email": "bob.smith@example.com",
      "recipient_id": "STU-002"
    },
    {
      "name": "Charlie Invalid",
      "email": "not-an-email-address",
      "recipient_id": "STU-003"
    }
  ]
}
```

#### Example `curl`
```bash
curl -X POST "http://localhost:8000/api/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "event_name": "Python Mastery Workshop",
    "issuer_name": "Data Academy",
    "recipients": [
      {"name": "Alice Smith", "email": "alice@example.com"},
      {"name": "Bob Jones", "email": "bob@example.com"}
    ]
  }'
```

---

### 2. Upload CSV or Excel (.xlsx) File for Bulk Generation
Upload a spreadsheet containing recipient rows (names, emails, IDs, grades) to automatically generate certificates.

* **Endpoint:** `POST /api/jobs/upload-file`
* **Status Code:** `202 Accepted`
* **Supported Formats:** `.csv`, `.xlsx`

#### Supported Column Headers (Case-Insensitive):
* **Name:** `name`, `recipient_name`, `full_name`, `fullname`, `student_name`
* **Email:** `email`, `recipient_email`, `email_address`
* **ID:** `recipient_id`, `id`, `student_id`, `roll_no`, `roll_number`, `emp_id`
* **Extra Columns:** Any other column (e.g., `Grade`, `Track`, `Score`) is automatically saved as `custom_attributes`!

#### Example `curl` for CSV Upload:
```bash
curl -X POST "http://localhost:8000/api/jobs/upload-file" \
  -F "file=@participants.csv" \
  -F "event_name=Cloud DevOps Bootcamp" \
  -F "issuer_name=Cloud Academy" \
  -F "certificate_title=Certificate of Completion"
```

#### Example `curl` for Excel (.xlsx) Upload:
```bash
curl -X POST "http://localhost:8000/api/jobs/upload-file" \
  -F "file=@students.xlsx" \
  -F "event_name=AI Machine Learning Symposium" \
  -F "issuer_name=Deep Learning Institute"
```


#### Response (`202 Accepted`)
```json
{
  "id": "e44d5678-8319-4a11-a83a-48fa88631b01",
  "event_name": "Python Mastery Workshop",
  "issuer_name": "Data Academy",
  "issue_date": "2026-10-15",
  "certificate_title": "Certificate of Achievement",
  "status": "PENDING",
  "total_count": 2,
  "success_count": 0,
  "failed_count": 0,
  "progress_percentage": 0.0,
  "created_at": "2026-10-11T14:40:00Z",
  "completed_at": null,
  "download_all_url": null,
  "certificates": [ ... ]
}
```

---

### 3. Check Job Status & Progress
Poll the job status and inspect individual recipient outcomes.

* **Endpoint:** `GET /api/jobs/{job_id}`
* **Status Code:** `200 OK`

#### Example `curl`
```bash
curl -X GET "http://localhost:8000/api/jobs/e44d5678-8319-4a11-a83a-48fa88631b01"
```

#### Response (`200 OK`)
```json
{
  "id": "e44d5678-8319-4a11-a83a-48fa88631b01",
  "event_name": "Python Mastery Workshop",
  "issuer_name": "Data Academy",
  "issue_date": "2026-10-15",
  "certificate_title": "Certificate of Achievement",
  "status": "PARTIAL_SUCCESS",
  "total_count": 3,
  "success_count": 2,
  "failed_count": 1,
  "progress_percentage": 100.0,
  "created_at": "2026-10-11T14:40:00Z",
  "completed_at": "2026-10-11T14:40:02Z",
  "download_all_url": "http://localhost:8000/api/jobs/e44d5678-8319-4a11-a83a-48fa88631b01/download-all",
  "certificates": [
    {
      "id": "cert-1111",
      "job_id": "e44d5678-8319-4a11-a83a-48fa88631b01",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice.johnson@example.com",
      "status": "SUCCESS",
      "file_name": "cert_Alice_Johnson_cert1111.pdf",
      "download_url": "http://localhost:8000/api/certificates/cert-1111/download",
      "error_message": null
    },
    {
      "id": "cert-2222",
      "job_id": "e44d5678-8319-4a11-a83a-48fa88631b01",
      "recipient_name": "Charlie Invalid",
      "recipient_email": "not-an-email-address",
      "status": "FAILED",
      "file_name": null,
      "download_url": null,
      "error_message": "Validation Error: Invalid email format: 'not-an-email-address'. Must be a valid email (e.g. user@domain.com)."
    }
  ]
}
```

---

### 4. Download All Certificates as ZIP
Downloads an on-demand bundled `.zip` archive containing all certificates that were successfully generated in the job.

* **Endpoint:** `GET /api/jobs/{job_id}/download-all`
* **Response Header:** `Content-Type: application/zip`

#### Example `curl`
```bash
curl -O -J "http://localhost:8000/api/jobs/e44d5678-8319-4a11-a83a-48fa88631b01/download-all"
```

---

### 5. Download Single Certificate PDF
Downloads the generated certificate for a specific recipient.

* **Endpoint:** `GET /api/certificates/{certificate_id}/download`
* **Response Header:** `Content-Type: application/pdf`

#### Example `curl`
```bash
curl -O -J "http://localhost:8000/api/certificates/cert-1111/download"
```

---

### 6. List All Jobs
Lists previous jobs with pagination support.

* **Endpoint:** `GET /api/jobs?skip=0&limit=20`

---

## Important Design Decisions

### Bulk Processing & Background Tasks
* **The Problem:** Generating hundreds or thousands of PDF documents takes noticeable processing time and file I/O. If processed synchronously in an HTTP request, the client would experience network timeouts (HTTP 504), blocking web server worker threads.
* **The Solution:** The API separates request ingestion from generation work. When a client submits a batch, the job record and pending certificates are immediately persisted, and an HTTP `202 Accepted` response is returned in milliseconds. Background processing is executed asynchronously via FastAPI's `BackgroundTasks`, updating progress incrementally in the database so clients can monitor progress via polling.

### Fault Isolation & Partial Success
* **The Requirement:** A single malformed recipient record must not crash or halt the entire batch.
* **The Solution:** In `services.py`, recipient data is validated item by item inside a fault-isolated try-catch block.
  * If a record contains invalid data (e.g. invalid email format or blank name), that individual certificate is flagged as `FAILED` with an explanatory `error_message`, and the job's `failed_count` is incremented.
  * Remaining valid certificates continue generating without interruption.
  * If all succeed: status is `COMPLETED`.
  * If some succeed and some fail: status is `PARTIAL_SUCCESS`.
  * If all fail: status is `FAILED`.

### Vector PDF Generation with ReportLab
* **Why ReportLab over HTML-to-PDF / Headless Browsers?**
  * Tools like WeasyPrint, wkhtmltopdf, or Puppeteer require system-level rendering engines, font servers, or Chromium binaries, which add installation complexity and heavy RAM consumption.
  * ReportLab is pure Python and generates exact, vector-sharp PDF coordinates. Text remains selectable and scalable at 300+ DPI print quality with minimal CPU overhead.

### Database Choice & Portability
* The data model links `Job (1) -> (N) Certificate` with cascade deletion.
* Production defaults to MySQL (`pymysql` driver) with connection pooling (`pool_size=10`, `pool_recycle=3600`).
* SQLite is automatically used in pytest tests (`sqlite:///:memory:`) using a `StaticPool`, ensuring tests run instantly and deterministically without dependencies on external services.

---

## Project Structure

```
Bulk_certificate_generator/
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment variables, DB URL, paths
│   ├── database.py            # SQLAlchemy engine, session maker, DB initialization
│   ├── models.py              # Job and Certificate database models
│   ├── schemas.py             # Pydantic v2 schemas and validators
│   ├── generator.py           # ReportLab PDF template generation engine
│   ├── services.py            # Bulk job creation, worker processing, zip bundling
│   └── routers/
│       ├── __init__.py
│       ├── jobs.py            # Job creation, status polling, and zip download
│       └── certificates.py    # Single certificate inspection and PDF download
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Test setup with in-memory SQLite fixture
│   ├── test_validation.py     # Schema and recipient validation tests
│   ├── test_jobs.py           # Job creation, processing, and listing tests
│   ├── test_failure_handling.py # Fault isolation and partial success tests
│   └── test_downloads.py      # PDF download and ZIP archive tests
├── generated_certificates/    # Local directory where generated files are stored
├── requirements.txt           # Project dependencies
├── .env.example               # Example configuration template
├── .env                       # Local environment configuration
├── main.py                    # Application entry point with FastAPI app
└── README.md                  # Complete documentation
```
