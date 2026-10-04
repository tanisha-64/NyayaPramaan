
"""

Document Reader — Gemini's native multimodal document understanding.

Works reliably for both text-based and scanned PDFs.

"""

from google import genai

import os

from dotenv import load_dotenv



load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))





def read_case_file_with_gemini(file_path: str) -> str:

    uploaded = client.files.upload(file=file_path)

    response = client.models.generate_content(

        model="gemini-3.6-flash",

        contents=[uploaded, "Extract the full text content of this legal document."],

    )

    return response.text

