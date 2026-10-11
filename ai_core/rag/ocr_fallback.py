"""
Free, local OCR fallback (Tesseract) — used when a PDF page has no extractable
text via pypdf (scanned/image-based page) and/or when the Gemini API is unavailable.
No API calls, no quota consumed.
"""

def ocr_page(file_path: str, page_number: int) -> str:
    """page_number is 1-indexed."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, first_page=page_number, last_page=page_number, dpi=200)
        if not images:
            return ""
        return pytesseract.image_to_string(images[0])
    except Exception as e:
        print(f"[ocr_fallback] OCR unavailable or failed on page {page_number}: {e}")
        return ""
