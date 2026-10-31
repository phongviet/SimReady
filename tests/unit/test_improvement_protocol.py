"""Preregistered matrix/access controls; no experimental scores."""

import importlib.util
from pathlib import Path


def module(name):
    spec = importlib.util.spec_from_file_location(name, Path("scripts") / (name + ".py"))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_frozen_partitions_cover_256_and_keep_pilot_out_of_train_test():
    splits, pilot = module("import_improvement_data").partitions()
    assert {k: len(v) for k, v in splits.items()} == {
        "train": 112,
        "validation": 32,
        "candidate": 48,
        "test": 64,
    }
    assert len(set(sum(splits.values(), []))) == 256
    assert set(pilot) <= set(splits["candidate"])
    assert not set(pilot) & set(splits["train"] + splits["validation"] + splits["test"])


def test_study_matrix_uses_frozen_policy_without_target_selection():
    m = module("run_improvement_studies")
    gen = dict(m.configs("generalization"))
    den = dict(m.configs("densification"))
    assert len(gen) == len(den) == 9
    assert (
        sum(c.iterations for c in gen.values()) * 2 + sum(c.iterations for c in den.values())
        == 82800
    )
    assert gen["selected-s42"].photometric_loss == "l1_ssim"
    assert gen["selected-s42"].iterations == 3600
    assert gen["original-s42"].iterations == 1200
    assert gen["matched-s42"].photometric_loss == "l1"
    assert {c.refine_stop for c in den.values()} == {900, 1800, 3000}
    assert {c.max_gaussians for c in den.values()} == {40000}
    assert all(c.checkpoint_steps == [1200, 2400, 3600] for c in den.values())
