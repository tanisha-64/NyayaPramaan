
"""

Object Storage wrapper — stores original case-files in Supabase Storage.

"""

from ai_core.rag.vector_store import get_supabase_client

import uuid



BUCKET_NAME = "case-files"





def upload_case_file(file_bytes: bytes, filename: str) -> str:

    client = get_supabase_client()

    unique_name = f"{uuid.uuid4()}_{filename}"

    client.storage.from_(BUCKET_NAME).upload(unique_name, file_bytes)

    return client.storage.from_(BUCKET_NAME).get_public_url(unique_name)

