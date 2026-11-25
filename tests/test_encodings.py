"""
Comprehensive unit tests for Stage 3:
  - Exhaustive correctness of all 5 AMO encodings (C1)
  - Exhaustive correctness of all 5 Exactly-K encodings (C2)
  - End-to-end SGP solving with Kissat across all C1 and C2 encodings (SAT & UNSAT)
"""

from itertools import product
import pytest
from pysat.solvers import Glucose3

from solvers.sat.encodings import AMO_ENCODERS, EXACTLY_K_ENCODERS
from solvers.sat.solver import solve_sgp


@pytest.mark.parametrize("amo_name", list(AMO_ENCODERS.keys()))
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 7, 8])
def test_amo_encodings_exhaustive(amo_name: str, n: int):
    """Exhaustively verify each AMO encoding accepts an assignment iff sum(x) <= 1."""
    encoder = AMO_ENCODERS[amo_name]
    lits = list(range(1, n + 1))
    clauses, top_id = encoder(lits, top_id=n)
    assert top_id >= n

    with Glucose3(bootstrap_with=clauses) as solver:
        for bits in product([0, 1], repeat=n):
            assumptions = [i if bits[i - 1] == 1 else -i for i in lits]
            sat = solver.solve(assumptions=assumptions)
            assert sat == (sum(bits) <= 1), (
                f"AMO '{amo_name}' mismatch for n={n}, bits={bits}: got sat={sat}"
            )


@pytest.mark.parametrize("eqk_name", list(EXACTLY_K_ENCODERS.keys()))
@pytest.mark.parametrize(
    "n,k",
    [(n, k) for n in range(2, 7) for k in range(0, n + 1)],
)
def test_exactly_k_encodings_exhaustive(eqk_name: str, n: int, k: int):
    """Exhaustively verify each Exactly-K encoding accepts an assignment iff sum(x) == k."""
    encoder = EXACTLY_K_ENCODERS[eqk_name]
    lits = list(range(1, n + 1))
    clauses, top_id = encoder(lits, k, top_id=n)
    assert top_id >= n

    with Glucose3(bootstrap_with=clauses) as solver:
        for bits in product([0, 1], repeat=n):
            assumptions = [i if bits[i - 1] == 1 else -i for i in lits]
            sat = solver.solve(assumptions=assumptions)
            assert sat == (sum(bits) == k), (
                f"Exactly-K '{eqk_name}' mismatch for n={n}, k={k}, bits={bits}: got sat={sat}"
            )


@pytest.mark.parametrize("c2_name", list(EXACTLY_K_ENCODERS.keys()))
@pytest.mark.parametrize(
    "g,p,w,expected_status",
    [
        (3, 2, 2, "SAT"),
        (4, 3, 3, "SAT"),
        (2, 2, 4, "UNSAT"),
        (3, 6, 6, "UNSAT"),
    ],
)
def test_all_c2_encodings_end_to_end_kissat(
    c2_name: str, g: int, p: int, w: int, expected_status: str
):
    """Verify all 5 C2 encodings produce consistent SAT/UNSAT and valid schedules with Kissat."""
    res = solve_sgp(
        g=g,
        p=p,
        w=w,
        group_size_encoding=c2_name,
        amo_encoding="pairwise",
        solver_name="kissat",
        timeout=30.0,
    )
    assert res.status == expected_status
    if expected_status == "SAT":
        assert res.is_valid is True, f"Invalid schedule for C2={c2_name}: {res.error_message}"


@pytest.mark.parametrize("c1_name", list(AMO_ENCODERS.keys()))
@pytest.mark.parametrize(
    "g,p,w,expected_status",
    [
        (3, 2, 2, "SAT"),
        (5, 3, 5, "SAT"),
        (3, 6, 6, "UNSAT"),
    ],
)
def test_all_c1_encodings_end_to_end_kissat(
    c1_name: str, g: int, p: int, w: int, expected_status: str
):
    """Verify all 5 C1 AMO encodings produce consistent SAT/UNSAT and valid schedules with Kissat."""
    res = solve_sgp(
        g=g,
        p=p,
        w=w,
        group_size_encoding="nsc",
        amo_encoding=c1_name,
        solver_name="kissat",
        timeout=30.0,
    )
    assert res.status == expected_status
    if expected_status == "SAT":
        assert res.is_valid is True, f"Invalid schedule for C1={c1_name}: {res.error_message}"
