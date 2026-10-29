import pytest

from simready.research.bench_analysis import ap50, class_accuracy


def prediction(box, score=0.9):
    return dict(box=box, score=score, label=15)


def test_perfect_duplicate_and_higher_ranked_false_positive():
    box = [0, 0, 10, 10]
    truth = {"a": [box]}
    assert ap50(truth, {"a": [prediction(box)]}, 15) == 1.0
    assert ap50(truth, {"a": []}, 15) == 0.0
    assert ap50(
        truth, {"a": [prediction([30, 30, 40, 40], 0.99), prediction(box)]}, 15
    ) == pytest.approx(0.5)
    counts = class_accuracy([box], [prediction(box), prediction(box, 0.8)], 15)
    assert (counts["tp"], counts["fp"], counts["fn"]) == (1, 1, 0)
    assert counts["precision"] == 0.5 and counts["recall"] == 1.0
    missed = class_accuracy([box], [], 15)
    assert missed["precision"] is None and missed["recall"] == 0 and missed["fn"] == 1
