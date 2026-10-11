"""
Document Reader — resilient text extraction, dispatched by file type so binary formats are never decoded as text.

* .pdf   -> pypdf (page boundaries kept as form-feeds), else Gemini multimodal fallback
* .docx  -> stdlib zip/XML (no extra dependency), else Gemini fallback
* .txt   -> UTF-8, only if it really looks like text
* images, legacy .doc, anything unreadable -> Gemini multimodal fallback (needs GEMINI_API_KEY)

Previously every format fell through to "decode the bytes as UTF-8", so a .docx (a zip archive) or an image was
accepted as "text" made of binary junk.
"""
import os
import re
import zipfile
from xml.etree import ElementTree

from dotenv import load_dotenv

load_dotenv()

NO_TEXT_MESSAGE = "No readable text content could be extracted from this document."
MIN_PDF_CHARS = 40
MIN_TEXT_CHARS = 20
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        # Pages are joined with a form-feed so page boundaries survive into case_text (the chunker's
        # text fallback uses them for real page citations). Empty pages keep their slot so numbering holds.
        extracted = [(page.extract_text() or "").strip() for page in reader.pages]
        if len("".join(extracted)) >= MIN_PDF_CHARS:
            return "\n\n\f".join(extracted).rstrip()
    except Exception as e:
        print(f"[document_reader] Local pdf extraction skipped/failed: {type(e).__name__}")
    return ""


def _read_docx(file_path: str) -> str:
    try:
        with zipfile.ZipFile(file_path) as z:
            root = ElementTree.fromstring(z.read("word/document.xml"))
        paragraphs = []
        for p in root.iter(f"{_W}p"):
            text = "".join(t.text or "" for t in p.iter(f"{_W}t"))
            if text.strip():
                paragraphs.append(text.strip())
        text = "\n\n".join(paragraphs)
        return text if len(text) >= MIN_TEXT_CHARS else ""
    except Exception as e:
        print(f"[document_reader] docx extraction skipped/failed: {type(e).__name__}")
        return ""


def _read_plain(file_path: str) -> str:
    try:
        with open(file_path, "rb") as f:
            raw = f.read()
        if b"\x00" in raw[:4096]:
            return ""                                   # NUL bytes: binary, not text
        text = raw.decode("utf-8", errors="ignore").strip()
        printable = sum(1 for c in text if c.isprintable() or c in "\n\r\t\f")
        if len(text) >= MIN_TEXT_CHARS and printable / max(len(text), 1) >= 0.9:
            return text
    except Exception:
        pass
    return ""


def _read_with_gemini(file_path: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        uploaded = client.files.upload(file=file_path)
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[uploaded, "Extract the full text content of this legal document verbatim."],
        )
        if response.text and len(response.text.strip()) > 0:
            return response.text
    except Exception as e:
        print(f"[document_reader] Gemini multimodal reader fallback failed: {type(e).__name__}")
    return ""


def ocr_pdf_sample(file_path: str, max_pages: int = 3) -> str:
    """Local OCR (Tesseract) of the first pages of a scanned PDF, used only so that a document with no text layer can
    still be classified by its CONTENT. Returns "" when OCR tooling is not installed or nothing is readable; nothing
    leaves the machine."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        parts = []
        for page in range(1, max_pages + 1):
            images = convert_from_path(file_path, first_page=page, last_page=page, dpi=200)
            if not images:
                break
            parts.append(pytesseract.image_to_string(images[0]) or "")
        return "\n\f".join(parts).strip()
    except Exception as e:
        print(f"[document_reader] local OCR sample unavailable: {type(e).__name__}")
        return ""


def read_case_file_with_gemini(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == ".pdf":
        text = _read_pdf(file_path)
    elif ext == ".docx":
        text = _read_docx(file_path)
    elif ext in (".txt", ""):
        text = _read_plain(file_path)
    if text:
        return text
    return _read_with_gemini(file_path) or NO_TEXT_MESSAGE
