"""
Document Reader (synopsis Section 4.2 -- RAG Engine)
Extracts full text from PDF case files via pypdf fast-path with Gemini 2.5 flash fallback.
"""
from google import genai
from pypdf import PdfReader
import os
from dotenv import load_dotenv

load_dotenv()

def read_case_file_with_gemini(file_path: str) -> str:
    # 0. Plain text files (.txt, .md, etc.)
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".txt", ".text", ".md", ".json"]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if len(content.strip()) >= 20:
                    return content
        except Exception as e:
            print(f"[document_reader] text file read notice: {e}")

    # 1. Fast local extraction (handles 99% of digital PDFs, petitions, judgments)
    try:
        reader = PdfReader(file_path)
        pages_text = []
        for p in reader.pages:
            t = p.extract_text()
            if t and t.strip():
                pages_text.append(t.strip())
        full = "\n\n".join(pages_text)
        if len(full.strip()) >= 50:
            return full
    except Exception as e:
        print(f"[document_reader] pypdf extraction notice: {e}")

    # 2. Fallback to Gemini Multimodal
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return ""
    try:
        client = genai.Client(api_key=api_key)
        uploaded = client.files.upload(file=file_path)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[uploaded, "Extract the full text content of this legal document accurately."],
        )
        return response.text or ""
    except Exception as e:
        print(f"[document_reader] Gemini extraction fallback error: {e}")
        return ""
