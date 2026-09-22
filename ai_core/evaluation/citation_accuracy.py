"""
Custom citation-accuracy metric (synopsis Section 4.6 impact table).
Tracks what fraction of cited judgments were genuinely retrieved (not hallucinated).
"""

def citation_accuracy(cited_case_names: list[str], retrieved_case_names: list[str]) -> float:
    if not cited_case_names:
        return 1.0
    verified = [c for c in cited_case_names if c in retrieved_case_names]
    return len(verified) / len(cited_case_names)