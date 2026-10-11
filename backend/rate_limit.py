"""
Minimal in-process sliding-window rate limiter (FastAPI dependencies).

Scope and limits - read before relying on it:
* State is per process. With several workers/instances each has its own counters, so the effective limit is
  limit x instances. It stops a single client hammering one instance (cost abuse of the LLM endpoints); it is not
  a distributed quota. Use an edge/WAF or Redis if you scale out.
* Authenticated routes are keyed by user id; public routes by client IP. Behind a proxy set TRUSTED_PROXY_HOPS
  (default 1, e.g. Render's load balancer): the client IP is then the entry that many hops from the RIGHT of
  X-Forwarded-For, so a client cannot choose its own key by sending a header.
* A limit of 0 disables that rule. Defaults can be overridden with the env vars named in RULES.
"""
import os
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request

from backend.auth.supabase_auth import get_current_user

# name: (env var, default max requests, window seconds)
RULES = {
    "ask":      ("RATE_LIMIT_ASK_PER_MIN", 30, 60),
    "upload":   ("RATE_LIMIT_UPLOAD_PER_HOUR", 20, 3600),
    "reindex":  ("RATE_LIMIT_REINDEX_PER_HOUR", 20, 3600),
    "search":   ("RATE_LIMIT_SEARCH_PER_MIN", 30, 60),
    "brief":    ("RATE_LIMIT_BRIEF_PER_MIN", 10, 60),
    "public":   ("RATE_LIMIT_PUBLIC_PER_MIN", 30, 60),
}

_lock = threading.Lock()
_hits: dict[tuple[str, str], deque] = defaultdict(deque)
_MAX_KEYS = 20000


def _limit_for(rule: str) -> tuple[int, int]:
    env, default, window = RULES[rule]
    try:
        return int(os.getenv(env, default)), window
    except ValueError:
        return default, window


def client_ip(request: Request) -> str:
    try:
        hops = max(1, int(os.getenv("TRUSTED_PROXY_HOPS", "1")))
    except ValueError:
        hops = 1
    forwarded = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    if len(forwarded) >= hops:
        return forwarded[-hops]
    return request.client.host if request.client else "unknown"


def check(rule: str, key: str, now: float | None = None) -> None:
    """Records a hit; raises 429 (with Retry-After) when the key exceeded the rule."""
    limit, window = _limit_for(rule)
    if limit <= 0:
        return
    now = time.monotonic() if now is None else now
    with _lock:
        if len(_hits) > _MAX_KEYS:                       # bound memory: drop keys whose window has fully expired
            for k in [k for k, q in _hits.items() if not q or now - q[-1] > 3600]:
                _hits.pop(k, None)
        q = _hits[(rule, key)]
        while q and now - q[0] >= window:
            q.popleft()
        if len(q) >= limit:
            retry = max(1, int(window - (now - q[0])) + 1)
            raise HTTPException(status_code=429, detail="Too many requests. Please slow down and try again shortly.",
                                headers={"Retry-After": str(retry)})
        q.append(now)


def reset() -> None:
    """Test helper."""
    with _lock:
        _hits.clear()


def limit_user(rule: str):
    """Dependency for authenticated routes: also returns the user so the route need not re-declare it."""
    def dep(user=Depends(get_current_user)):
        check(rule, str(user.id))
        return user
    return dep


def limit_ip(rule: str):
    def dep(request: Request):
        check(rule, client_ip(request))
    return dep
