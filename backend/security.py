"""
Authorization helpers. The backend talks to Supabase with the SERVICE ROLE key, which bypasses RLS, so every
route that touches user-owned rows must prove ownership here. Ownership failures and missing rows return the
same 404 so ids cannot be probed for existence.
"""
import os
import re
import uuid

from fastapi import HTTPException

NOT_FOUND = "Not found"

# Mirrors frontend/services/documentService.ts (ACCEPTED_FORMATS / 50MB).
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"}
_PDF_MAGIC = b"%PDF-"


def max_upload_bytes() -> int:
    try:
        return int(float(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024)
    except ValueError:
        return 50 * 1024 * 1024


def max_cases_per_user() -> int:
    try:
        return int(os.getenv("MAX_CASES_PER_USER", "200"))
    except ValueError:
        return 200


def clean_uuid(value, what: str = "resource") -> str:
    """Canonical lowercase UUID string, or 404 (never reveals whether the id was merely malformed)."""
    try:
        return str(uuid.UUID(str(value).strip()))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=404, detail=NOT_FOUND)


def get_owned_case(client, case_id, user_id, columns: str = "id") -> dict:
    cid = clean_uuid(case_id)
    res = client.table("cases").select(columns).eq("id", cid).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return res.data[0]


def get_owned_session(client, session_id, user_id, columns: str = "id") -> dict:
    sid = clean_uuid(session_id)
    res = client.table("chat_sessions").select(columns).eq("id", sid).eq("user_id", user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return res.data[0]


def safe_filename(filename: str | None) -> str:
    """Basename only, restricted charset, bounded length. Used for storage keys and the stored filename."""
    name = os.path.basename((filename or "").replace("\\", "/")).strip()
    name = re.sub(r"[^\w.\- ()\[\]]+", "_", name, flags=re.UNICODE).strip(" ._")
    return (name or "document")[:150]


def max_pdf_pages() -> int:
    try:
        return int(os.getenv("MAX_PDF_PAGES", "600"))
    except ValueError:
        return 600


# Leading bytes each accepted binary format must start with. The extension alone is user-controlled, so it is never
# trusted: a renamed executable or an archive posing as a PDF is refused before any parser or LLM sees it.
_MAGIC = {
    ".docx": (b"PK\x03\x04",),
    ".doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".tiff": (b"II*\x00", b"MM\x00*"),
    ".bmp": (b"BM",),
    ".webp": (b"RIFF",),
}


def _inspect_pdf(data: bytes) -> None:
    """Rejects PDFs the pipeline cannot read: password-protected, structurally corrupt, or absurdly long."""
    import io
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            # Many PDFs are "encrypted" with an empty user password and read fine; only a real password blocks us.
            try:
                opened = reader.decrypt("")
            except Exception:
                opened = 0
            if not opened:
                raise HTTPException(status_code=422, detail="This PDF is password-protected. Please remove the password and upload it again.")
        pages = len(reader.pages)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="This PDF appears to be corrupted or unreadable. Please upload a valid copy.")
    if pages == 0:
        raise HTTPException(status_code=422, detail="This PDF has no pages.")
    if pages > max_pdf_pages():
        raise HTTPException(status_code=413, detail=f"This PDF has too many pages (limit {max_pdf_pages()}).")


def validate_upload(filename: str | None, data: bytes) -> str:
    """Returns the lowercase extension (with dot) or raises 400/413/415/422. Checks the real bytes, not just the name."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file format.")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > max_upload_bytes():
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {max_upload_bytes() // (1024 * 1024)}MB.")
    if ext == ".pdf":
        if not data.lstrip()[:5] == _PDF_MAGIC:
            raise HTTPException(status_code=415, detail="The file does not look like a valid PDF.")
        _inspect_pdf(data)
    elif ext == ".txt":
        if b"\x00" in data[:4096]:
            raise HTTPException(status_code=415, detail="The file does not look like a plain-text document.")
    else:
        magics = _MAGIC.get(ext, ())
        if magics and not data.startswith(magics):
            raise HTTPException(status_code=415, detail=f"The file content does not match its {ext} extension.")
        if ext == ".webp" and data[8:12] != b"WEBP":
            raise HTTPException(status_code=415, detail="The file content does not match its .webp extension.")
    return ext
