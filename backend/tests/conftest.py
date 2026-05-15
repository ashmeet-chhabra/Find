"""
conftest.py – patch heavy dependencies before find_api is imported.

Sets a SQLite DATABASE_URL so no PostgreSQL/psycopg2 is needed, and stubs
out pgvector (which requires a live Postgres extension) and MinIO storage.
"""

import sys
import os
from unittest.mock import MagicMock, patch
import sqlalchemy

# ---------------------------------------------------------------------------
# 1. Point DATABASE_URL at SQLite so no psycopg2 is needed.
# ---------------------------------------------------------------------------
# Hard-pin these so tests never accidentally hit real DB/Redis/MinIO even if
# those env vars are set in the host environment.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["MINIO_ENDPOINT"] = "localhost:9000"
os.environ["MINIO_ACCESS_KEY"] = "minioadmin"
os.environ["MINIO_SECRET_KEY"] = "minioadmin"
os.environ["MINIO_BUCKET"] = "find-images"

# ---------------------------------------------------------------------------
# 2. Patch create_engine to strip kwargs unsupported by SQLite (pool_size,
#    max_overflow) so database.py module-level call succeeds.
# ---------------------------------------------------------------------------
_orig_create_engine = sqlalchemy.create_engine


def _sqlite_safe_create_engine(url, **kwargs):
    kwargs.pop("pool_size", None)
    kwargs.pop("max_overflow", None)
    kwargs.setdefault("connect_args", {"check_same_thread": False})
    return _orig_create_engine(url, **kwargs)


sqlalchemy.create_engine = _sqlite_safe_create_engine  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 3. Stub pgvector before SQLAlchemy tries to use the Vector column type.
# ---------------------------------------------------------------------------
pgvector_mock = MagicMock()
pgvector_mock.sqlalchemy.Vector = MagicMock(return_value=MagicMock())
sys.modules.setdefault("pgvector", pgvector_mock)
sys.modules.setdefault("pgvector.sqlalchemy", pgvector_mock.sqlalchemy)

# ---------------------------------------------------------------------------
# 4. Stub minio so storage.py doesn't fail at import.
# ---------------------------------------------------------------------------
minio_mock = MagicMock()
minio_error_mock = MagicMock()
minio_error_mock.S3Error = Exception
sys.modules.setdefault("minio", minio_mock)
sys.modules.setdefault("minio.error", minio_error_mock)

# ---------------------------------------------------------------------------
# 5. Stub rq so queue.py doesn't fail without a Redis connection at import.
# ---------------------------------------------------------------------------
rq_mock = MagicMock()
sys.modules.setdefault("rq", rq_mock)
sys.modules.setdefault("rq.job", rq_mock)

# ---------------------------------------------------------------------------
# 6. Stub redis so queue.py can import Redis without the real package.
# ---------------------------------------------------------------------------
redis_mock = MagicMock()
redis_mock.Redis = MagicMock()
sys.modules.setdefault("redis", redis_mock)
