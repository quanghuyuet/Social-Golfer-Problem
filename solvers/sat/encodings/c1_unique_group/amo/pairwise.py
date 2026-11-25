"""
Pairwise encoding for At-Most-One (AMO) constraints (Constraint C1).
"""

from itertools import combinations
from typing import List, Tuple


def encode_amo_pairwise(
    literals: List[int], top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode At-Most-One (sum(literals) <= 1) using Pairwise encoding."""
    if len(literals) <= 1:
        return [], top_id
    clauses = [[-a, -b] for a, b in combinations(literals, 2)]
    return clauses, top_id
