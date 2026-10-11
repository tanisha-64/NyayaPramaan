"""
Object Storage wrapper — stores original case-files in Supabase Storage.

The bucket SHOULD be private (see sql/proposed/002_security_rls.sql notes). Callers get a time-limited signed
URL; if the bucket is still public the signed URL simply works as well.
"""
import uuid

from ai_core.rag.vector_store import get_supabase_client
from backend.security import safe_filename

BUCKET_NAME = "case-files"
SIGNED_URL_TTL_SECONDS = 3600


def upload_case_file(file_bytes: bytes, filename: str) -> str:
    safe_name = safe_filename(filename)
    try:
        client = get_supabase_client()
        unique_name = f"{uuid.uuid4()}_{safe_name}"      # basename only: no path traversal into other keys
        client.storage.from_(BUCKET_NAME).upload(unique_name, file_bytes)
        try:
            signed = client.storage.from_(BUCKET_NAME).create_signed_url(unique_name, SIGNED_URL_TTL_SECONDS)
            url = (signed or {}).get("signedURL") or (signed or {}).get("signedUrl")
            if url:
                return url
        except Exception:
            pass
        return client.storage.from_(BUCKET_NAME).get_public_url(unique_name)
    except Exception as e:
        print(f"[supabase_storage] Storage upload notice: {type(e).__name__}")
        return f"/cases/{safe_name}"
