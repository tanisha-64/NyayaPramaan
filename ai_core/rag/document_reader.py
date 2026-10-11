
"""
Document Reader — resilient text extraction for PDF, TXT, and scanned files.
Uses local pypdf extraction first (instant, zero-dependency on external APIs)
with fallback to OCR/GenAI if text is scanned or sparse.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def read_case_file_with_gemini(file_path: str) -> str:
    # 1. Fast local text extraction via pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        extracted = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                extracted.append(t)
        full_text = "\n\n".join(extracted).strip()
        if len(full_text) >= 40:
            return full_text
    except Exception as e:
        print(f"[document_reader] Local pdf extraction skipped/failed: {e}")

    # 2. Plain text / utf-8 fallback
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read().strip()
            if len(text) >= 20:
                return text
    except Exception:
        pass

    # 3. Gemini Vision / Multimodal fallback if API key is present
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
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
            print(f"[document_reader] Gemini multimodal reader fallback failed: {e}")

    return "No readable text content could be extracted from this document."


