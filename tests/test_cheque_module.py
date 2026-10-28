from datetime import date

from ai_core.rag.cheque_deadlines import add_months, compute
from ai_core.rag.legal_scope import in_scope, suggestions_for, topic_sections
from ai_core.rag.statutes import explicit_lookup


def test_add_months_clamps():
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)


def test_full_timeline():
    r = compute(date(2026, 8, 1), date(2026, 9, 10), notice_sent=date(2026, 9, 20), notice_received=date(2026, 9, 22),
                presented=date(2026, 8, 20), today=date(2026, 10, 1))
    d = {s["key"]: s["date"] for s in r["steps"]}
    assert d["notice"] == "2026-10-10" and d["payment"] == "2026-10-07"
    assert d["cause"] == "2026-10-08" and d["complaint"] == "2026-11-08"


def test_only_bank_date_gives_notice_deadline_and_asks_for_more():
    r = compute(date(2026, 8, 1), date(2026, 9, 10), today=date(2026, 9, 11))
    assert [s["key"] for s in r["steps"]] == ["presentation", "notice"]
    assert any("Notice" in w for w in r["warnings"])


def test_late_presentation_and_late_notice_flagged():
    r = compute(date(2026, 3, 1), date(2026, 9, 10), presented=date(2026, 9, 1), notice_sent=date(2026, 11, 1), today=date(2026, 11, 2))
    assert r["steps"][0]["status"] == "missed" and len(r["warnings"]) >= 3


def test_cheque_topic_and_scope():
    assert ("NI", "138") in topic_sections("cheque bounce ho gaya")
    assert in_scope("cheque bounce kya karu") and "notice" in suggestions_for("cheque bounce")[0].lower()


def test_ni_explicit_lookup():
    assert explicit_lookup("section 138 NI Act") == ("NI", "138")
    assert explicit_lookup("NI Act 138") == ("NI", "138")
    assert explicit_lookup("Negotiable Instruments Act 138") == ("NI", "138")
    assert explicit_lookup("IPC 302") == ("IPC", "302")