"""The gate calibration table in eval/run_eval.py."""

import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("run_eval", Path(__file__).resolve().parents[1] / "eval" / "run_eval.py")
run_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_eval)


def test_calibration_counts_each_error_and_marks_the_current_row():
    table = "\n".join(run_eval.calibration_table(pos=[0.9, 0.8, 0.3], neg=[0.01, 0.15], hard=[0.95, 0.5, 0.05], current=0.10))
    assert "| **0.10** | 0/3 (0%) | 1/2 (50%) | 2/3 (67%) |" in table  # 0.15 negative passes at 0.10
    assert "| 0.20 | 0/3 (0%) | 0/2 (0%) | 2/3 (67%) |" in table
    assert "| 0.40 | 1/3 (33%) | 0/2 (0%) |" in table  # the 0.3 positive is now refused
    assert "no gate error on this set: 0.20 to 0.30" in table


def test_kinds_and_hard_negative_grading():
    from types import SimpleNamespace

    assert run_eval.kind_of({"fact": "MUE.64450"}) == "fact"
    assert run_eval.kind_of({"hard_negative": True}) == "hard"
    assert run_eval.kind_of({"negative": True}) == "negative" and run_eval.kind_of({}) == "positive"
    item = {"must_not_match": ["\\$\\s?\\d"]}
    assert run_eval.hard_negative_clean(item, SimpleNamespace(answerable=False, text=""))
    assert run_eval.hard_negative_clean(item, SimpleNamespace(answerable=True, text="The manual does not list payment."))
    assert not run_eval.hard_negative_clean(item, SimpleNamespace(answerable=True, text="Medicare pays $95."))
