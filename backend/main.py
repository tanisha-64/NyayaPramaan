"""
FastAPI entrypoint (synopsis Section 4.2 -- Application Services).
Includes security headers, crash resilience middleware, and rate limiting.
"""
import time
import logging
from collections import defaultdict
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import (
    chat_router,
    document_router,
    case_router,
    search_router,
    admin_router,
    quiz_router,
    news_router,
    game_router,
)

logger = logging.getLogger("nyayapramaan.api")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="NyayaPramaan API",
    description="Evidence-backed legal intelligence platform with cryptographic audit trail",
    version="2.0.0",
)

# 1. CORS Configuration (Strict Allowed Origins)
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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Sliding Window In-Memory Rate Limiter (Protection against DoS / brute force)
RATE_LIMIT_RECORD = defaultdict(list)
RATE_LIMIT_MAX_REQUESTS = 120  # 120 requests per minute per IP
RATE_LIMIT_WINDOW = 60  # seconds

@app.middleware("http")
async def security_and_rate_limit_middleware(request: Request, call_next):
    # Exempt health checks and OPTIONS preflight
    if request.url.path == "/health" or request.method == "OPTIONS":
        response = await call_next(request)
        return response

    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean old requests outside the sliding window
    RATE_LIMIT_RECORD[client_ip] = [
        t for t in RATE_LIMIT_RECORD[client_ip] if now - t < RATE_LIMIT_WINDOW
    ]

    if len(RATE_LIMIT_RECORD[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "error": "Rate limit exceeded. Please wait a moment before sending more requests.",
                "retry_after_seconds": RATE_LIMIT_WINDOW,
            },
        )

    RATE_LIMIT_RECORD[client_ip].append(now)

    try:
        response = await call_next(request)
    except Exception as exc:
        logger.error(f"[Unhandled Exception Crash Guard] {request.method} {request.url.path}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "An unexpected error occurred while processing your request.",
                "status": "error",
            },
        )

    # Inject Enterprise Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# 3. Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"[Global Exception Handler] {request.url.path} failed: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error. Our system team has been notified."},
    )


# 4. Route Registration
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
    return {"status": "ok", "service": "NyayaPramaan API", "timestamp": time.time()}