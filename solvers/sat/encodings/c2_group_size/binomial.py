"""
Direct Binomial encoding for Exactly-K constraints (Constraint C2 — Eq. 13-14).
"""

from itertools import combinations
from typing import List, Tuple


def encode_exactly_k_binomial(
    literals: List[int], k: int, top_id: int
) -> Tuple[List[List[int]], int]:
    """
    Encode sum(literals) == k using direct Binomial encoding (Equations 13-14).

    Warning: Generates C(n, n-k+1) + C(n, k+1) clauses; exponential in n and k.
    """
    n = len(literals)
    if k < 0 or k > n:
        return [[]], top_id
    if k == 0:
        return [[-x] for x in literals], top_id
    if k == n:
        return [[x] for x in literals], top_id

    clauses: List[List[int]] = []
    # Eq. (13): At least k
    for subset in combinations(literals, n - k + 1):
        clauses.append(list(subset))
    # Eq. (14): At most k
    for subset in combinations(literals, k + 1):
        clauses.append([-x for x in subset])

    return clauses, top_id
