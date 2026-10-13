import os
import shutil
import sqlite3
import tempfile
from sqlite3 import Connection
import logging

logger = logging.getLogger(__name__)


def _resolve_db_path() -> str:
    """Determine a valid, writable path for SQLite across local and cloud environments."""
    # 1. Custom explicit path from DATABASE_URL
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url.startswith("sqlite:///"):
        custom_path = db_url[len("sqlite:///"):]
        if custom_path:
            # If serverless, ensure path is writable in /tmp
            if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
                if not os.path.isabs(custom_path):
                    custom_path = os.path.join(tempfile.gettempdir(), custom_path)
            return custom_path

    # 2. Serverless environment detection (Vercel / AWS Lambda)
    is_serverless = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    default_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    default_db_path = os.path.join(default_dir, "adapted.db")

    if is_serverless:
        tmp_dir = os.path.join(tempfile.gettempdir(), "capabl_data")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception:
            tmp_dir = tempfile.gettempdir()
        tmp_db_path = os.path.join(tmp_dir, "adapted.db")

        # If a pre-existing database was shipped with repo, copy it to /tmp
        if os.path.exists(default_db_path) and not os.path.exists(tmp_db_path):
            try:
                shutil.copy2(default_db_path, tmp_db_path)
            except Exception as e:
                logger.warning(f"Could not copy initial database to {tmp_db_path}: {e}")
        return tmp_db_path

    # 3. Check if local directory is writable
    try:
        os.makedirs(default_dir, exist_ok=True)
        test_file = os.path.join(default_dir, ".write_test")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return default_db_path
    except (OSError, PermissionError):
        # Fallback to temp directory on read-only filesystem
        tmp_dir = os.path.join(tempfile.gettempdir(), "capabl_data")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
        except Exception:
            tmp_dir = tempfile.gettempdir()
        tmp_db_path = os.path.join(tmp_dir, "adapted.db")
        if os.path.exists(default_db_path) and not os.path.exists(tmp_db_path):
            try:
                shutil.copy2(default_db_path, tmp_db_path)
            except Exception:
                pass
        return tmp_db_path


DB_PATH = _resolve_db_path()


def get_db_connection() -> Connection:
    global DB_PATH
    db_path = _resolve_db_path()
    DB_PATH = db_path
    db_dir = os.path.dirname(db_path)
    if db_dir:
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass

    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn
