from fastapi import FastAPI, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db.session import engine


settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)


@app.get("/health", tags=["health"])
def application_health() -> dict[str, str]:
    """Report whether the API process is available."""
    return {"status": "ok"}


@app.get("/health/database", tags=["health"])
def database_health() -> dict[str, str]:
    """Verify that the API can reach PostgreSQL."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from error

    return {"status": "ok"}
