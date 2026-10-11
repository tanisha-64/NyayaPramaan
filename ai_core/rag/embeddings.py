
"""

Embeddings — current google-genai SDK, gemini-embedding-001 model,

with a batch function for fast multi-page document indexing.

"""

from google import genai

from google.genai import types

import os

from dotenv import load_dotenv



load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

EMBEDDING_MODEL = "gemini-embedding-001"





def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:

    result = client.models.embed_content(

        model=EMBEDDING_MODEL, contents=text,

        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),

    )

    return result.embeddings[0].values





def embed_texts_batch(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:

    if not texts:

        return []

    result = client.models.embed_content(

        model=EMBEDDING_MODEL, contents=texts,

        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=768),

    )

    return [e.values for e in result.embeddings]

