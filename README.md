# PulseShip Backend

A college package-tracking project built with **FastAPI**, **synchronous PyMongo**, and **MongoDB Atlas**.

One modular backend handles:
- Registration and cookie-based login.
- Order creation, viewing, and cancellation.
- Courier assignment, acceptance, and delivery updates.
- Admin order management and soft deletion.

## Requirements

- Python 3.12.
- MongoDB Atlas connection string and permitted network access.

## Setup

Run from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Configure `.env`:

```dotenv
MONGODB_URI=YOUR_ATLAS_CONNECTION_STRING
MONGODB_DATABASE=PulseShip

SESSION_SECRET=YOUR_RANDOM_SECRET_AT_LEAST_32_CHARACTERS_LONG
SESSION_HTTPS_ONLY=false
SESSION_MAX_AGE=28800

PUBLIC_ORIGIN=http://localhost:5173
API_ORIGIN=http://127.0.0.1:8000
```

Generate a session secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env` or real credentials.

## Initialize the Database

```bash
python -m scripts.init_db
python -m scripts.seed_demo_data
```

These scripts create missing collections, indexes, and demo accounts without
overwriting existing accounts.

## Run

```bash
python -m uvicorn app.main:app --reload
```

- Interactive API docs: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health/live`
- Database readiness: `http://127.0.0.1:8000/health/ready`

## Demo Accounts

| Role | Email | Password |
|---|---|---|
| User | seller@example.com | seller-demo |
| Courier | courier1@example.com | courier1-demo |
| Courier | courier2@example.com | courier2-demo |
| Admin | admin@example.com | admin-demo |

Existing accounts are left unchanged by the seed script.

## Frontend Integration

The React frontend runs at `http://localhost:5173` and proxies `/api` requests
to the backend.

Login uses an automatic HttpOnly session cookie—no tokens or identity headers.

## Documentation

- `docs/api-contract.md`: endpoints and business rules.
- `plan.md`: development plan and project progress.

## Limitations

Classroom demonstration only: use fictional data and passwords.
Application passwords are stored in plaintext; this is not production-ready.
Automated API tests are currently skipped.