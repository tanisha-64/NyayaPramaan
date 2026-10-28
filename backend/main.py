"""
FastAPI entrypoint. FRONTEND_URL and allowed origins are configured so CORS works
in local dev, preview deployments, and production (Render/Vercel) without mismatch.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from backend.routers import wizard_router

load_dotenv()

from backend.routers import chat_router, document_router, case_router, search_router, admin_router, quiz_router, news_router, game_router
from backend.routers import tools_router

app = FastAPI(title="NyayaPramaan API")

def get_allowed_origins() -> list[str]:
    origins = {
        "https://nyaya-pramaan.vercel.app",
        "https://nyayapramaan.vercel.app",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    }
    env_frontend = os.getenv("FRONTEND_URL", "")
    if env_frontend:
        for u in env_frontend.split(","):
            cleaned = u.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)
    env_allowed = os.getenv("ALLOWED_ORIGINS", "")
    if env_allowed:
        for u in env_allowed.split(","):
            cleaned = u.strip().rstrip("/")
            if cleaned:
                origins.add(cleaned)
    return list(origins)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_origin_regex=r"https://(nyaya-pramaan|nyayapramaan)(-[a-z0-9-]+)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router.router, prefix="/chat")
app.include_router(wizard_router.router, prefix="/wizards", tags=["wizards"])
app.include_router(document_router.router, prefix="/document")
app.include_router(case_router.router, prefix="/case")
app.include_router(search_router.router, prefix="/search")
app.include_router(admin_router.router, prefix="/admin")
app.include_router(quiz_router.router, prefix="/quiz")
app.include_router(news_router.router, prefix="/news")
app.include_router(game_router.router, prefix="/game")
app.include_router(tools_router.router, prefix="/tools", tags=["tools"])


@app.get("/health")
def health():
    return {"status": "ok"}
