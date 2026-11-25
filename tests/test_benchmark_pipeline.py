"""
Unit tests for Stage 4 benchmark pipeline:
  - Dataset loading (66 instances from dataset/data.txt)
  - Crash-safe CSV logging & resume skipping
  - Binomial MEMOUT guard
  - End-to-end mini benchmark run
"""

from pathlib import Path
from benchmark.benchmark_sat import (
    estimate_binomial_total_clauses,
    run_benchmark,
)
from benchmark.common import (
    AXIS2_REPRESENTATIVE_INSTANCES,
    INTERACTION_CHECK_INSTANCES,
    SGPInstance,
    load_instances,
)
from benchmark.csv_log import SATCSVLogger, load_csv_rows


def test_load_dataset_has_66_instances():
    instances = load_instances(sort_by_size=True)
    assert len(instances) == 66
    names = {inst.name for inst in instances}
    for req in AXIS2_REPRESENTATIVE_INSTANCES:
        assert req in names, f"Missing Axis 2 instance {req} in dataset/data.txt"
    for req in INTERACTION_CHECK_INSTANCES:
        assert req in names, f"Missing interaction instance {req} in dataset/data.txt"


def test_binomial_clause_estimator_and_memout_guard():
    small = SGPInstance(3, 2, 2)
    large = SGPInstance(5, 10, 5)
    assert estimate_binomial_total_clauses(small) < 1_000
    assert estimate_binomial_total_clauses(large) > 10**10


def test_benchmark_runner_and_resume(tmp_path: Path):
    out_csv = tmp_path / "test_results.csv"

    # First run: 2 smallest instances x 5 C2 encodings = 10 runs
    executed_1 = run_benchmark(
        experiment="c2",
        output_csv=out_csv,
        timeout=30.0,
        sort_by_size=True,
        overwrite=True,
        limit=2,
        verbose=False,
    )
    assert executed_1 == 10
    rows = load_csv_rows(out_csv)
    assert len(rows) == 10
    for row in rows:
        assert row["status"] in ("SAT", "UNSAT", "MEMOUT")
        if row["status"] == "SAT":
            assert row["is_valid"] == "True"

    # Second run without overwrite: should skip all 10 already-completed runs
    executed_2 = run_benchmark(
        experiment="c2",
        output_csv=out_csv,
        timeout=30.0,
        sort_by_size=True,
        overwrite=False,
        limit=2,
        verbose=False,
    )
    assert executed_2 == 0
    assert len(load_csv_rows(out_csv)) == 10
