"""
At-Least-One (ALO) encoding for Constraint C1 (Unique Group Assignment).
"""

from typing import List


def encode_alo(literals: List[int]) -> List[List[int]]:
    """
    Encode At-Least-One (sum(literals) >= 1) as a single disjunction clause:
        (x_1 | x_2 | ... | x_g)
    """
    return [list(literals)]
