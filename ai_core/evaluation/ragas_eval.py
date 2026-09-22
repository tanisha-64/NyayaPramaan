"""
Evaluation Layer (synopsis Section 4.2, 4.4)
Uses the actual RAGAS framework (Es et al., 2023), configured with Gemini
via RAGAS's native Google-provider support (google-genai SDK) -- no OpenAI
key, no local HuggingFace models, no torch. This keeps the evaluation layer
genuinely RAGAS-based, exactly as specified in the synopsis, while remaining
lightweight and fully API-based.
"""
import os
import asyncio
from dotenv import load_dotenv
from google import genai
from ragas import SingleTurnSample
from ragas.llms import llm_factory
from ragas.metrics import Faithfulness

load_dotenv()

_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_llm = llm_factory("gemini-3.6-flash", provider="google", client=_client)
_faithfulness = Faithfulness(llm=_llm)


async def _score_faithfulness_async(question: str, answer: str, contexts: list[str]) -> float:
    sample = SingleTurnSample(
        user_input=question,
        response=answer,
        retrieved_contexts=contexts,
    )
    return await _faithfulness.single_turn_ascore(sample)


def score_faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    """RAGAS faithfulness score (0.0-1.0): does the answer stick only to what
    the retrieved evidence actually supports?"""
    return asyncio.run(_score_faithfulness_async(question, answer, contexts))