# Full-Stack Warehouse Management System

A full-stack application for managing warehouse inventory and operations.

## Development status

Backend batches 1–8 are complete or partially verified. Batch 9 provides the
frontend foundation and authentication screens.

## Backend foundation

The backend uses FastAPI, PostgreSQL 16, SQLAlchemy and Alembic. Start the
database with `docker compose up -d`, then run the API with
`./.venv/bin/uvicorn app.main:app --app-dir backend --reload`.

## Frontend authentication

Serve the `frontend` directory on port 5500, for example:

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`. The frontend calls `http://localhost:8000/api/v1`
by default. To use another API address, set `window.WMS_API_BASE_URL` before
loading the JavaScript bundle.
