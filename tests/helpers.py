import io
import json
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.auth.supabase_auth import get_current_user
from backend.main import app

USER_A = SimpleNamespace(id="11111111-1111-1111-1111-111111111111", email="a@example.test")
USER_B = SimpleNamespace(id="22222222-2222-2222-2222-222222222222", email="b@example.test")


def make_pdf(pages: int = 1, password: str | None = None) -> bytes:
    from pypdf import PdfWriter
    writer, buf = PdfWriter(), io.BytesIO()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    if password is not None:
        writer.encrypt(password)
    writer.write(buf)
    return buf.getvalue()


def make_text_pdf(pages: list[str]) -> bytes:
    """A real, text-searchable PDF (one page per string; "" gives a page with no text, like a scan). Hand-built so the
    tests need no PDF-writing dependency."""
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    objs: list[bytes] = []
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_id = 3 + 2 * len(pages)
    for i, text in enumerate(pages):
        content_id = 4 + 2 * i
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents {content_id} 0 R "
                    f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>".encode())
        lines = [l for l in text.split("\n") if l.strip()]
        ops = ["BT", "/F1 10 Tf", "50 750 Td", "12 TL"] + [f"({esc(l)}) '" for l in lines] + ["ET"] if lines else []
        stream = "\n".join(ops).encode("latin-1", "replace")
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


@contextmanager
def signed_in(user, db, extra_patches=()):
    """TestClient authenticated as `user`, with every module that talks to Supabase pointed at the in-memory `db`."""
    app.dependency_overrides[get_current_user] = lambda: user
    targets = ["backend.routers.chat_router.get_supabase_client", "backend.routers.case_router.get_supabase_client",
               "backend.routers.document_router.get_supabase_client", "ai_core.rag.vector_store.get_supabase_client",
               "ai_core.rag.document_chunker.get_supabase_client", "trust_log.hash_chain.get_supabase_client"]
    patchers = [patch(t, return_value=db) for t in targets] + list(extra_patches)
    for p in patchers:
        p.start()
    try:
        yield TestClient(app)
    finally:
        for p in patchers:
            p.stop()
        app.dependency_overrides.clear()


def completion_response(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


class ScriptedLLM:
    """Stands in for litellm.completion. `rules` is a list of (marker, reply-or-callable): the first rule whose marker
    appears in the prompt answers. Every prompt is recorded so tests can assert what was (not) sent to a provider."""

    def __init__(self, rules, default=None):
        self.rules, self.default, self.prompts = list(rules), default, []

    def __call__(self, model=None, messages=None, **kwargs):
        prompt = messages[0]["content"]
        self.prompts.append(prompt)
        for marker, reply in self.rules:
            if marker in prompt:
                text = reply(prompt) if callable(reply) else reply
                if isinstance(text, Exception):
                    raise text
                return completion_response(text if isinstance(text, str) else json.dumps(text))
        if self.default is not None:
            return completion_response(self.default)
        raise RuntimeError("no scripted reply for prompt: " + prompt[:120])

    def sent(self, needle: str) -> bool:
        return any(needle in p for p in self.prompts)
