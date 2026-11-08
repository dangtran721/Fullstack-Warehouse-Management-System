FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY backend ./backend

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
