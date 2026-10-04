
"""

FastAPI entrypoint. FRONTEND_URL is read from env so CORS works in both

local dev and production (Render) without code changes.

"""

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

import os

from dotenv import load_dotenv



load_dotenv()



from backend.routers import chat_router, document_router, case_router, search_router, admin_router, quiz_router, news_router, game_router



app = FastAPI(title="NyayaPramaan API")



FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")



app.add_middleware(

    CORSMiddleware,

    allow_origins=[FRONTEND_URL, "http://localhost:3000"],

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

