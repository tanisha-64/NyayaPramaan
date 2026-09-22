"""
FastAPI entrypoint (synopsis Section 4.2 -- Application Services).
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers import chat_router, document_router, case_router, search_router, admin_router, quiz_router, news_router, game_router

app = FastAPI(title="NyayaPramaan API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(chat_router.router, prefix="/chat")
app.include_router(document_router.router, prefix="/document")
app.include_router(case_router.router, prefix="/case")
app.include_router(search_router.router, prefix="/search")
app.include_router(admin_router.router, prefix="/admin")
app.include_router(quiz_router.router, prefix="/quiz")
app.include_router(news_router.router, prefix="/news")
app.include_router(game_router.router, prefix="/game")

@app.get("/health")
def health():
    return {"status": "ok"}