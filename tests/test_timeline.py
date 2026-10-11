"""Timeline builder: every event is a date that literally appears in the document, with its sentence and page."""
import re

from ai_core.timeline.extractor import (
    extract_timeline, extract_timeline_events, find_dates, classify_event, is_timeline_query, timeline_evidence_chunks,
    NO_DATES_MESSAGE,
)
from tests import sample_docs as S


def by_date(events):
    return {e["date"]: e for e in events}


def test_events_carry_source_page_and_verbatim_sentence():
    events = extract_timeline_events(S.JUDGMENT_TEXT)
    got = by_date(events)
    assert got["12 March 2019"]["page"] == 1 and "instituted this suit" in got["12 March 2019"]["text"]
    assert got["14 January 2018"]["page"] == 2
    assert got["30 November 2021"]["page"] == 4
    full = re.sub(r"\s+", " ", S.JUDGMENT_TEXT.replace("\f", " "))
    for e in events:
        core = e["text"].strip("…").strip()
        assert core in full, f"event text must be copied from the document, not generated: {core!r}"
        assert not e["page_estimated"]


def test_a_date_alone_is_not_treated_as_a_hearing_that_took_place():
    got = by_date(extract_timeline_events(S.JUDGMENT_TEXT))
    assert got["05.08.2021"]["event_type"] == "hearing" and got["05.08.2021"]["status"] == "recorded"      # "was heard on"
    same_day = [e for e in extract_timeline_events(S.JUDGMENT_TEXT) if e["date"] == "14 September 2021"]
    assert len(same_day) == 2                                   # para 10 (listed) and para 11 (adjournment sought)
    assert any(e["status"] == "scheduled" for e in same_day)    # "listed for further hearing on" -> not yet a recorded hearing
    assert not any(e["status"] == "recorded" and e["event_type"] == "hearing" for e in same_day)
    listed = got["12 October 2021"]
    assert listed["event_type"] == "hearing" and listed["status"] == "scheduled"                         # "next date was fixed for"
    assert "listed/next date" in listed["label"] and "recorded" not in listed["label"]
    sentence = "The respondent was born on 4 March 1980 in Rampur."
    assert classify_event(sentence) == ("other", "mentioned")                                              # not a hearing, not an order


def test_one_sentence_with_two_events_labels_each_date_by_its_own_clause():
    got = by_date(extract_timeline_events("The matter was heard on 5 May 2020 and adjourned to 7 June 2020 by the court."))
    assert (got["5 May 2020"]["event_type"], got["5 May 2020"]["status"]) == ("hearing", "recorded")
    assert (got["7 June 2020"]["event_type"], got["7 June 2020"]["status"]) == ("hearing", "scheduled")
    lead = by_date(extract_timeline_events("On 12.03.2019, the plaintiff filed the suit for declaration of title and possession."))
    assert lead["12.03.2019"]["event_type"] == "filing", "a bare 'On <date>,' clause borrows the next clause"


def test_numbered_paragraphs_do_not_leak_into_the_previous_sentence():
    text = "9. The matter was heard on 05.08.2021 and arguments were heard. 10. The case was then listed for further hearing on 14 September 2021."
    got = by_date(extract_timeline_events(text))
    assert got["05.08.2021"]["status"] == "recorded" and "listed" not in got["05.08.2021"]["text"]
    assert got["14 September 2021"]["status"] == "scheduled"


def test_hearing_word_without_a_marker_stays_unconfirmed():
    assert classify_event("Reference is made to the hearing of 3 May 2020 in the records.") == ("hearing", "mentioned")
    label_line = extract_timeline("The hearing of 3 May 2020 is referred to in the file notes of the registry for reference.")
    assert "Hearing (date mentioned)" in label_line and "recorded" not in label_line


def test_order_filing_fir_and_deadline_types():
    got = by_date(extract_timeline_events(S.JUDGMENT_TEXT))
    assert got["30 November 2021"]["event_type"] == "order"
    assert got["12 March 2019"]["event_type"] == "filing"
    fir = extract_timeline_events(S.FIR_TEXT)
    assert any(e["event_type"] == "fir" for e in fir)
    assert classify_event("The accused shall deposit the amount within 30 days of 1 May 2020.")[0] == "deadline"


def test_chronological_order_and_dd_mm_yyyy_normalisation():
    events = extract_timeline_events(S.JUDGMENT_TEXT)
    isos = [e["iso"] for e in events if e["iso"]]
    assert isos == sorted(isos)
    assert by_date(events)["05.08.2021"]["iso"] == "2021-08-05"          # Indian dd.mm.yyyy


def test_impossible_or_ambiguous_dates_are_not_guessed():
    dates = {d[2]: d[3] for d in find_dates("Dated 31.02.2020 and 15.13.2020 and 12 Marchh 2020 and 7/8/2021.")}
    assert dates["31.02.2020"] is None and dates["15.13.2020"] is None       # kept as written, no normalised guess
    assert "12 Marchh 2020" not in dates
    assert dates["7/8/2021"] == "2021-08-07"


def test_years_and_amounts_are_not_dates():
    assert find_dates("In 2019 the sum of 4,50,000 and case no. 118/2019 and section 138 were discussed.") == []
    assert extract_timeline("Nothing dated appears in this short text about a land dispute in the village.") == NO_DATES_MESSAGE
    assert extract_timeline("") == NO_DATES_MESSAGE


def test_string_contract_is_unchanged_and_carries_page_references():
    text = extract_timeline(S.JUDGMENT_TEXT)
    lines = text.splitlines()
    assert all(l.startswith("- ") and " -- " in l for l in lines)
    assert any("12 March 2019 -- Filing" in l and l.endswith("(Page 1)") for l in lines)


def test_estimated_pages_are_flagged_when_the_text_has_no_page_breaks():
    text = " ".join(f"Sentence {i} filler about the dispute." for i in range(150)) + " The suit was filed on 3 March 2019. " + \
           " ".join(f"More filler sentence {i} here." for i in range(150))
    events = extract_timeline_events(text)
    assert events and events[0]["page_estimated"] is True
    assert "Page ~" in extract_timeline(text)


def test_events_are_bounded():
    text = "\n".join(f"On {d:02d}.{m:02d}.2020 the matter was heard by the court in session." for m in range(1, 13) for d in range(1, 29))
    assert len(extract_timeline_events(text)) <= 150


def test_timeline_question_detection():
    for q in ("When was the next hearing?", "give me the timeline of this case", "what dates are mentioned",
              "agli tareekh kab hai", "सुनवाई की तारीख क्या है", "list all orders passed"):
        assert is_timeline_query(q), q
    for q in ("Who is the plaintiff?", "What is the punishment for theft?"):
        assert not is_timeline_query(q), q


def test_timeline_evidence_chunks_are_page_tagged_and_scoped():
    chunks = timeline_evidence_chunks(S.JUDGMENT_TEXT, "case-1", limit=3)
    assert len(chunks) == 3 and all(c["case_id"] == "case-1" and c["page_number"] and c["chunk_text"] for c in chunks)
