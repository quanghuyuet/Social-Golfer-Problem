"""
Product encoding for At-Most-One (AMO) constraints (Constraint C1).

Reference:
    J. Chen, "A New SAT Encoding of the At-Most-One Constraint",
    ModRef 2010.
"""

import math
from itertools import combinations
from typing import List, Tuple


def encode_amo_product(
    literals: List[int], top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode At-Most-One (sum(literals) <= 1) using the 2D Product encoding."""
    n = len(literals)
    if n <= 1:
        return [], top_id
    if n <= 4:
        return [[-a, -b] for a, b in combinations(literals, 2)], top_id

    p = math.isqrt(n)
    if p * p < n:
        p += 1
    q = math.ceil(n / p)

    clauses: List[List[int]] = []
    next_id = top_id

    row_vars = []
    for _ in range(p):
        next_id += 1
        row_vars.append(next_id)

    col_vars = []
    for _ in range(q):
        next_id += 1
        col_vars.append(next_id)

    for idx, lit in enumerate(literals):
        r = idx // q
        c = idx % q
        clauses.append([-lit, row_vars[r]])
        clauses.append([-lit, col_vars[c]])

    row_clauses, next_id = encode_amo_product(row_vars, next_id)
    clauses.extend(row_clauses)
    col_clauses, next_id = encode_amo_product(col_vars, next_id)
    clauses.extend(col_clauses)

    return clauses, next_id
