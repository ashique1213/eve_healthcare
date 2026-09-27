# Eve Healthcare — Diagnostic Booking & Payment Backend Service

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.2-green.svg)](https://www.djangoproject.com/)
[![REST Framework](https://img.shields.io/badge/DRF-3.18-red.svg)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-red.svg)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-5.4-green.svg)](https://docs.celeryq.dev/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)

A production-grade, asynchronous, and idempotent backend microservice for managing **diagnostic test bookings** and **simulated payment gateway processing**.

---

## Key Features

1. **JWT-Based Authentication**:
   - User Registration (`/api/auth/register/`) & Login (`/api/auth/login/`)
   - Role-Based Access Control (**PATIENT** vs **ADMIN**)
   - JWT Access & Refresh token rotation and blacklisting

2. **Diagnostic Centres & Tests Catalog**:
   - Manage Diagnostic Centres, Master Test Catalog, and per-centre Pricing & Turnaround Times (`CentreTest`)
   - Advanced search, filtering by city/category, and pagination
   - Admin-only write access with read-only public access

3. **Diagnostic Test Booking System**:
   - Booking creation with future datetime validation and test price verification
   - Human-friendly unique booking reference codes (e.g., `BK-20260925-A1B2C3`)
   - State Machine workflow: `PENDING` -> `CONFIRMED` / `FAILED` / `CANCELLED`
   - Patient isolation (patients only see their own bookings; admins see all)

4. **Simulated Payment Processing**:
   - Endpoint (`POST /api/payments/`) to simulate payment gateway outcomes (`SUCCESS` / `FAILED`)
   - Automatic booking status transition based on payment result
   - Strict transaction bounds preventing payment on already confirmed or cancelled bookings

5. **Guaranteed Idempotent Payment Webhook**:
   - Webhook Endpoint (`POST /api/payments/webhook/`) accepting gateway event notifications
   - **Strict Idempotency Guarantee**: Duplicate event deliveries (`event_id`) or repeated retries do NOT create duplicate payment records, duplicate bookings, or corrupt DB state
   - Atomic database locking (`select_for_update`) ensuring thread safety during high-concurrency event bursts

6. **Bonus Engineering Features**:
   - **Redis Caching**: Caching catalogue queries with signal-based cache invalidation
   - **Celery Background Jobs**: Asynchronous booking notification dispatch and expired pending booking cleanup tasks
   - **Docker & Docker Compose**: Full containerization setup (Django Web, PostgreSQL, Redis, Celery Worker)
   - **OpenAPI 3.0 & Swagger UI**: Interactive API documentation rendered at `/api/docs/`
   - **Comprehensive Test Suite**: Unit & integration tests achieving **93% test coverage**
   - **Throttling & Rate Limiting**: Protection against API spam and webhook flooding

---

## Architecture & Database Schema Design

### Entity-Relationship Diagram (ERD)

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│      User       │       │ DiagnosticCentre│       │  DiagnosticTest  │
├─────────────────┤       ├─────────────────┤       ├──────────────────┤
│ id (UUID)       │       │ id (UUID)       │       │ id (UUID)        │
│ username        │       │ name            │       │ name             │
│ email           │       │ location        │       │ code (Unique)    │
│ role            │       │ city            │       │ category         │
└────────┬────────┘       └────────┬────────┘       └────────┬─────────┘
         │ 1                       │ 1                       │ 1
         │                         │                         │
         │ N                       │ N                       │ N
┌────────┴────────┐       ┌────────┴─────────────────────────┴──────────┐
│     Booking     │       │                CentreTest                   │
├─────────────────┤       ├─────────────────────────────────────────────┤
│ id (UUID)       │       │ id (UUID)                                   │
│ booking_ref     │ N ──► │ centre_id (FK)                              │
│ user_id (FK)    │       │ test_id (FK)                                │
│ centre_test (FK)│       │ price (Decimal)                             │
│ appointment_time│       │ is_available (Bool)                         │
│ amount (Decimal)│       └─────────────────────────────────────────────┘
│ status (Enum)   │
└────────┬────────┘
         │ 1
         │
         │ N
┌────────┴────────┐       ┌─────────────────┐
│     Payment     │       │   WebhookLog    │
├─────────────────┤       ├─────────────────┤
│ id (UUID)       │       │ id (UUID)       │
│ transaction_id  │       │ event_id (Unique│
│ booking_id (FK) │       │ event_type      │
│ amount          │       │ payload (JSON)  │
│ status (Enum)   │       │ status (Enum)   │
└─────────────────┘       └─────────────────┘
```

### Booking State Machine Transition

```
                        ┌───────────┐
                        │  PENDING  │
                        └─────┬─────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
      ┌──────────────┐ ┌──────────────┐ ┌───────────┐
      │  CONFIRMED   │ │    FAILED    │ │ CANCELLED │
      └──────────────┘ └──────────────┘ └───────────┘
```

---

## How to Run Locally

### Option 1: Using Docker & Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/eve-healthcare.git
   cd eve-healthcare
   ```

2. **Start all services**:
   ```bash
   docker compose up --build
   ```

3. Services will start automatically:
   - **Web API**: `http://localhost:8000`
   - **Swagger Docs**: `http://localhost:8000/api/docs/`
   - **PostgreSQL**: `localhost:5432`
   - **Redis**: `localhost:6379`
   - **Celery Worker**: Background task processing

---

### Option 2: Local Python Virtual Environment

1. **Create and activate virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\Activate.ps1
   # On Linux/macOS:
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

4. **Run Migrations & Seed Initial Data**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py seed_data
   ```

5. **Run the Development Server**:
   ```bash
   python manage.py runserver
   ```

6. **Run Celery Worker (Optional for background jobs)**:
   ```bash
   celery -A eve_healthcare worker --loglevel=info
   ```

---

## Running Unit & Integration Tests

The test suite contains **33 tests** covering authentication, centre pricing, bookings, payments, and idempotent webhook edge cases.

```bash
pytest
```

To view HTML coverage report:
```bash
pytest --cov=apps --cov-report=html
```

---

## API Endpoints & Example Requests

### Pre-seeded Credentials (from `python manage.py seed_data`)
- **Admin**: `username: admin` | `password: Admin@123456`
- **Patient**: `username: john_doe` | `password: Patient@123456`

---

### 1. User Registration & Login

#### Signup (`POST /api/auth/register/`)
```bash
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "sarah_connor",
    "email": "sarah@example.com",
    "password": "Password123!",
    "password_confirm": "Password123!",
    "first_name": "Sarah",
    "last_name": "Connor",
    "phone_number": "+19876543210"
  }'
```

#### Login (`POST /api/auth/login/`)
```bash
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "Patient@123456"
  }'
```
*Response*: Returns JWT `access` token and `refresh` token.

---

### 2. Diagnostic Centres & Tests Catalog

#### List Diagnostic Centres (`GET /api/centres/`)
```bash
curl -X GET "http://localhost:8000/api/centres/?search=Indiranagar"
```

#### List Diagnostic Tests (`GET /api/centres/tests/`)
```bash
curl -X GET http://localhost:8000/api/centres/tests/
```

#### List Centre Test Pricings (`GET /api/centres/pricings/`)
```bash
curl -X GET http://localhost:8000/api/centres/pricings/
```

---

### 3. Booking System

#### Create a Diagnostic Booking (`POST /api/bookings/`)
```bash
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "centre_test": "<CENTRE_TEST_UUID>",
    "appointment_datetime": "2026-10-15T10:30:00Z",
    "notes": "Fasting sample collection required."
  }'
```

#### List User's Bookings (`GET /api/bookings/`)
```bash
curl -X GET http://localhost:8000/api/bookings/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

#### Cancel Booking (`POST /api/bookings/<BOOKING_ID>/cancel/`)
```bash
curl -X POST http://localhost:8000/api/bookings/<BOOKING_ID>/cancel/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"
```

---

### 4. Simulated Payment Endpoint

#### Process Simulated Payment (`POST /api/payments/`)
```bash
curl -X POST http://localhost:8000/api/payments/ \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "booking_id": "BK-20260925-4255F1",
    "payment_method": "CARD",
    "status": "SUCCESS"
  }'
```
*Result*: Updates booking status to `CONFIRMED` and returns payment receipt.

---

### 5. Payment Gateway Webhook (Idempotent)

#### Receive Webhook Event (`POST /api/payments/webhook/`)
```bash
curl -X POST http://localhost:8000/api/payments/webhook/ \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "evt_gateway_10001",
    "event_type": "payment.success",
    "booking_id": "BK-20260925-4255F1",
    "transaction_id": "txn_gateway_55555",
    "amount": 450.00,
    "status": "SUCCESS"
  }'
```

#### Testing Idempotency:
Send the **exact same command** a second time.
- **Output**: Returns `200 OK` with `{"is_duplicate": true, "status": "already_processed"}`.
- **Verification**: No duplicate payments created; booking state preserved intact.

---

## Important Assumptions Made

1. **Centre-Test Relationship (`CentreTest`)**:
   Different diagnostic centres offer tests at different prices and turnaround times. The `CentreTest` junction table bridges `DiagnosticCentre` and `DiagnosticTest` and stores location-specific pricing.

2. **Idempotency Strategy**:
   Webhooks rely on a combination of a unique `event_id` in `WebhookLog` and `transaction_id` in `Payment`. Database-level unique constraints and atomic `select_for_update` queries prevent race conditions.

3. **Booking Cancellation**:
   A booking can only be cancelled if its current status is `PENDING` or `CONFIRMED`.

4. **Currency**:
   Amounts are specified in INR (Rs) with standard decimal precision (`DecimalField(max_digits=10, decimal_places=2)`).

---

## What I Would Improve With More Time

1. **Distributed Lock (Redis Redlock)**:
   For high-throughput distributed deployments across multiple Django app nodes, use Redis Redlock for cross-process idempotency locking before hitting PostgreSQL.

2. **Time Slot Management**:
   Implement dynamic slot availability (e.g. max 5 appointments per 30-minute interval per centre) to avoid overbooking diagnostic technicians.

3. **Websocket / Server-Sent Events (SSE)**:
   Use Django Channels for real-time frontend notifications when payment webhooks arrive.

4. **Prometheus Metrics & Grafana Dashboard**:
   Expose custom metrics (`booking_created_total`, `payment_success_rate`, `webhook_duplicates_count`).
