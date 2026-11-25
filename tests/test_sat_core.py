"""
Unit tests for Stage 2: NSC encoding, NSE model, Kissat solver, and SGP Verifier.
"""

from itertools import product
import pytest
from pysat.solvers import Glucose3

from benchmark.verify import verify_schedule
from solvers.sat.encodings.c2_group_size.nsc import encode_exactly_k_nsc
from solvers.sat.model import SGPModel
from solvers.sat.solver import solve_sgp


@pytest.mark.parametrize(
    "n,k",
    [(n, k) for n in range(2, 7) for k in range(0, n + 1)],
)
def test_nsc_exactness_exhaustive(n: int, k: int):
    """Exhaustively verify NSC clauses accept an assignment iff sum(x) == k."""
    lits = list(range(1, n + 1))
    clauses, top_id = encode_exactly_k_nsc(lits, k, top_id=n)

    # Check auxiliary variable count formula from Paper Table 1 for 1 <= k < n
    if 1 <= k < n:
        expected_aux = k * (n - 1) - (k * (k - 1)) // 2
        assert top_id - n == expected_aux

    with Glucose3(bootstrap_with=clauses) as solver:
        for bits in product([0, 1], repeat=n):
            assumptions = [i if bits[i - 1] == 1 else -i for i in lits]
            sat = solver.solve(assumptions=assumptions)
            assert sat == (sum(bits) == k), (
                f"NSC mismatch for n={n}, k={k}, bits={bits}: got sat={sat}"
            )


@pytest.mark.parametrize(
    "g,p,w,expected_vars",
    [
        (3, 2, 2, 63),
        (4, 3, 3, 384),
        (5, 3, 2, 345),
        (5, 3, 3, 615),
        (5, 4, 4, 1450),
        (6, 3, 8, 2880),
    ],
)
def test_nse_nsc_variable_counts_match_paper_table10(g: int, p: int, w: int, expected_vars: int):
    """Verify NSE_NSC total variable counts match Paper Table 10 exactly."""
    model = SGPModel(g, p, w, group_size_encoding="nsc", amo_encoding="pairwise")
    cnf = model.build()
    assert cnf.nv == expected_vars


@pytest.mark.parametrize(
    "g,p,w",
    [
        (2, 2, 3),
        (3, 2, 2),
        (4, 3, 3),
        (5, 3, 5),
        (5, 3, 7),
        (5, 4, 4),
    ],
)
def test_kissat_sat_instances(g: int, p: int, w: int):
    """Verify Kissat solves known SAT instances and produces valid SGP schedules."""
    res = solve_sgp(g, p, w, solver_name="kissat", timeout=30.0)
    assert res.status == "SAT", f"Expected SAT for {g}-{p}-{w}, got {res.status}"
    assert res.schedule is not None
    assert res.is_valid is True, f"Invalid schedule for {g}-{p}-{w}: {res.error_message}"


@pytest.mark.parametrize(
    "g,p,w",
    [
        (2, 2, 4),
        (3, 6, 6),
        (3, 8, 5),
        (5, 8, 3),
    ],
)
def test_kissat_unsat_instances(g: int, p: int, w: int):
    """Verify Kissat proves UNSAT on known unsatisfiable instances."""
    res = solve_sgp(g, p, w, solver_name="kissat", timeout=30.0)
    assert res.status == "UNSAT", f"Expected UNSAT for {g}-{p}-{w}, got {res.status}"
    assert res.schedule is None


def test_verifier_catches_invalid_schedules():
    """Verify that the independent verifier rejects all 3 classes of SGP violations."""
    # Valid 2-2-3 schedule
    valid = [
        [[1, 2], [3, 4]],
        [[1, 3], [2, 4]],
        [[1, 4], [2, 3]],
    ]
    ok, _ = verify_schedule(2, 2, 3, valid)
    assert ok is True

    # 1. Wrong group size
    bad_size = [
        [[1, 2, 3], [4]],
        [[1, 3], [2, 4]],
        [[1, 4], [2, 3]],
    ]
    ok, _ = verify_schedule(2, 2, 3, bad_size)
    assert ok is False

    # 2. Player assigned twice in same week
    bad_assignment = [
        [[1, 2], [2, 4]],
        [[1, 3], [2, 4]],
        [[1, 4], [2, 3]],
    ]
    ok, _ = verify_schedule(2, 2, 3, bad_assignment)
    assert ok is False

    # 3. Duplicate pairing across weeks (1 and 2 meet in both week 1 and week 2)
    bad_pairing = [
        [[1, 2], [3, 4]],
        [[1, 2], [3, 4]],
        [[1, 4], [2, 3]],
    ]
    ok, _ = verify_schedule(2, 2, 3, bad_pairing)
    assert ok is False
