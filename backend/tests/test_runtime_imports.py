"""Regression test for lazy database-driver initialization."""
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_application_import_does_not_load_psycopg() -> None:
    command = [
        sys.executable,
        "-c",
        "import sys; from app.main import app; assert 'psycopg' not in sys.modules; print(app.title)",
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        env={"PYTHONPATH": str(PROJECT_ROOT / "backend")},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Warehouse Management System"
