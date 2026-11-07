# Full-Stack Warehouse Management System

A full-stack application for managing warehouse inventory and operations.

## Development status

Project initialization is in progress.

## Backend foundation

The backend uses FastAPI, PostgreSQL 16, SQLAlchemy and Alembic. Start the
database with `docker compose up -d`, then run the API with
`./.venv/bin/uvicorn app.main:app --app-dir backend --reload`.
