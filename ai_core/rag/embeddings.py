"""
Embeddings — current google-genai SDK, gemini-embedding-001 model,
with a batch function for fast multi-page document indexing.

The client is created lazily so importing this module (tests, tooling, CI) does not require GEMINI_API_KEY.
Every vector is validated (non-empty, exactly EMBEDDING_DIM numbers) before it is returned: a wrong-sized or missing
vector would otherwise be written to pgvector or fail there, so it is rejected here with a clear error instead.
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIM = 768          # must match the vector(768) column / RPC signatures in Supabase
_client = None


class EmbeddingError(RuntimeError):
    """The provider returned nothing usable (wrong count, empty or wrong-sized vectors)."""


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def _validated(values, what: str) -> list[float]:
    vec = list(values or [])
    if len(vec) != EMBEDDING_DIM:
        raise EmbeddingError(f"{what}: expected {EMBEDDING_DIM} dimensions, got {len(vec)}")
    return vec


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    if not text or not text.strip():
        raise EmbeddingError("cannot embed empty text")
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL, contents=text,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM),
    )
    if not result.embeddings:
        raise EmbeddingError("provider returned no embedding")
    return _validated(result.embeddings[0].values, "embedding")


def embed_texts_batch(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    if not texts:
        return []
    if any(not t or not t.strip() for t in texts):
        raise EmbeddingError("cannot embed empty text")
    result = _get_client().models.embed_content(
        model=EMBEDDING_MODEL, contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBEDDING_DIM),
    )
    embeddings = result.embeddings or []
    if len(embeddings) != len(texts):
        raise EmbeddingError(f"provider returned {len(embeddings)} embeddings for {len(texts)} texts")
    return [_validated(e.values, f"embedding {i}") for i, e in enumerate(embeddings)]
