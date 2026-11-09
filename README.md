# Warehouse Management System

Warehouse management application using FastAPI, PostgreSQL 16, and a static
HTML/CSS/Vanilla JavaScript frontend.

## Live demo

| Resource | URL |
| --- | --- |
| Source code | https://github.com/dangtran721/Fullstack-Warehouse-Management-System |
| Frontend | https://fullstack-warehouse-management-syst.vercel.app |
| Login page | https://fullstack-warehouse-management-syst.vercel.app/pages/login.html |
| Backend API | https://fullstack-warehouse-management-system-production.up.railway.app |
| Swagger API docs | https://fullstack-warehouse-management-system-production.up.railway.app/docs |
| API health check | https://fullstack-warehouse-management-system-production.up.railway.app/health |

### Demo accounts

| Role | Username | Email | Password | Status |
| --- | --- | --- | --- | --- |
| STAFF | `demo_staff` | `staff@wms-demo.com` | `Demo123456` | Active and verified |
| ADMIN | `techstation_admin` | `admin@techstation-demo.com` | `TechStationAdmin2026!` | Active and verified |

The credentials above are intentionally public and must be used only for this
hosted demo. Do not reuse them for a production deployment.

## Features

- JWT access/refresh authentication with rotation and ADMIN/STAFF roles.
- Products, categories, units, suppliers, and multiple warehouses.
- Import, export, transfer, adjustment, inventory history, and low-stock alerts.
- DRAFT → CONFIRMED/CANCELLED document workflows. ADMIN may export below zero;
  STAFF may not. Transfers and adjustments never create negative stock.

## Prerequisites

- Docker Desktop with Docker Compose.
- Python 3.12 for local development and tests.
- Node.js 20+ for frontend unit tests.

## Configuration

Copy `.env.example` to `.env`, then set a unique `POSTGRES_PASSWORD` and a
random `JWT_SECRET_KEY` of at least 32 characters. Never commit `.env`.

`CORS_ALLOWED_ORIGINS` must list the origins used to serve the static frontend.

## Run with Docker Compose

Start PostgreSQL and the API:

```bash
docker compose up --build -d
```

Apply migrations after the database is healthy:

```bash
docker compose run --rm api python -m alembic -c backend/alembic.ini upgrade head
```

Verify the API:

```bash
curl http://localhost:8000/health
```

Stop the local stack with `docker compose down`. This does not remove the
named database volume; use `docker compose down -v` only when intentionally
discarding local development data.

## Run frontend

The frontend is static. With the API running on port 8000:

```bash
cd frontend
python3 -m http.server 5500
```

Open `http://localhost:5500`. The default API URL is
`http://localhost:8000/api/v1`. A deployment can set
`window.WMS_API_BASE_URL` before loading the frontend bundle.

## Railway + Vercel deployment

1. Create a Railway project from this GitHub repository and add a PostgreSQL
   service. Railway uses `railway.toml` and the root Dockerfile.
2. In Railway set `DATABASE_URL` to its PostgreSQL connection URL,
   `JWT_SECRET_KEY` to a newly generated secret, `DEBUG=false`, and set
   `CORS_ALLOWED_ORIGINS` after Vercel provides the frontend URL.
3. In Vercel import the same repository with **Root Directory** set to
   `frontend`. Set `API_BASE_URL` to `/api/v1`. The Vercel rewrite in
   `frontend/vercel.json` securely proxies that same-origin path to Railway.
4. Add the final Vercel URL to Railway's `CORS_ALLOWED_ORIGINS`, redeploy the
   API, then check `/health`, `/docs`, registration, and login.

The current hosted demo uses:

- Frontend: `https://fullstack-warehouse-management-syst.vercel.app`
- API: `https://fullstack-warehouse-management-system-production.up.railway.app`

The production container applies outstanding Alembic migrations before it
starts the API, so a clean Railway PostgreSQL database receives the schema on
its first successful deployment.

Neither `JWT_SECRET_KEY` nor database passwords are committed. The frontend
build writes its runtime API endpoint from Vercel's
`API_BASE_URL` environment variable.

## Local development and migrations

Create a Python 3.12 virtual environment, install the project plus dev
dependencies, then run:

```bash
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --reload
PYTHONPATH=backend .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
```

Public registration creates STAFF accounts only. Create an ADMIN through an
approved administrative/database setup in a non-production environment; the
application intentionally has no hard-coded account or password.

## Tests

Run backend tests with an isolated test database for PostgreSQL tests:

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q
node --test frontend/tests/auth.test.mjs
```

Set `WMS_TEST_DATABASE_URL` only to a disposable database before running the
PostgreSQL concurrency and E2E tests. Do not point it at development data.

## Verification limits

- PostgreSQL API E2E and row-lock concurrency have been verified on isolated
  databases.
- Browser-driven E2E, console, and network capture are not verified because
  local browser automation is disabled by the current Work settings.
- The FastAPI/TestClient dependency emits a deprecation warning during tests.
