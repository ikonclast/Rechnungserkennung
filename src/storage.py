"""storage.py — MinIO-Wrapper.

Liest Credentials aus Umgebungsvariablen (identisch mit docker-compose.yml).
Bucket-Name kommt aus MINIO_BUCKET_INVOICES (Default: "invoices").

Beispiel:
    from src.storage import upload, exists
    path = upload("/tmp/rechnung.pdf", "ab12cd34/rechnung.pdf")
    print(exists("ab12cd34/rechnung.pdf"))  # True
"""

import os

from minio import Minio
from minio.error import S3Error

_ENDPOINT  = os.getenv("MINIO_ENDPOINT", "localhost:9000")
_ACCESS    = os.getenv("MINIO_ROOT_USER", "minioadmin")
_SECRET    = os.getenv("MINIO_ROOT_PASSWORD", "")
_BUCKET    = os.getenv("MINIO_BUCKET_INVOICES", "invoices")


def _client() -> Minio:
    return Minio(_ENDPOINT, access_key=_ACCESS, secret_key=_SECRET, secure=False)


def ensure_bucket() -> None:
    c = _client()
    if not c.bucket_exists(_BUCKET):
        c.make_bucket(_BUCKET)


def upload(local_path: str, object_name: str) -> str:
    """Lädt eine Datei in MinIO hoch. Gibt 'bucket/object_name' zurück."""
    ensure_bucket()
    _client().fput_object(_BUCKET, object_name, local_path)
    return f"{_BUCKET}/{object_name}"


def exists(object_name: str) -> bool:
    """Prüft ob ein Objekt im Bucket existiert."""
    try:
        _client().stat_object(_BUCKET, object_name)
        return True
    except S3Error:
        return False
