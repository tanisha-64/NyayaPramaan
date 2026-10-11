import pytest

from ai_core.rag.lexical import Bm25, reciprocal_rank_fusion, tokens


def test_tokens_preserve_unicode_and_numeric_identifiers():
    assert tokens("Section 303—न्याय / IPC") == ["section", "303", "न्याय", "ipc"]


def test_bm25_scores_matching_documents_and_reports_query_coverage():
    index = Bm25(["theft under section 303", "contract dispute", "theft theft section"])

    scores, coverage = index.scores("theft 303")

    assert len(scores) == len(coverage) == 3
    assert scores[0] > scores[2] > scores[1]
    assert coverage == [1.0, 0.0, 0.5]


@pytest.mark.parametrize("documents,query", [([], "theft"), (["theft"], "")])
def test_bm25_empty_input_returns_zero_scores_and_coverage(documents, query):
    scores, coverage = Bm25(documents).scores(query)

    assert scores == [0.0] * len(documents)
    assert coverage == [0.0] * len(documents)


def test_reciprocal_rank_fusion_combines_weighted_rankings_once_per_list():
    fused = reciprocal_rank_fusion(
        [["a", "b", "a"], ["b", "c"]],
        weights=[1.0, 2.0],
        k=0,
    )

    assert fused == {"a": 1.0, "b": 2.0, "c": 1.0}


def test_reciprocal_rank_fusion_rejects_mismatched_weights():
    with pytest.raises(ValueError, match="one value per ranking"):
        reciprocal_rank_fusion([["a"]], weights=[])
