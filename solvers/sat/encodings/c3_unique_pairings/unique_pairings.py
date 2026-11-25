"""
Direct 4-literal clause encoding for Constraint C3 (Unique Pairings — Eq. 10).

Reference:
    T. V. Kieu, N. T. Nguyen, and K. V. To,
    "An Efficient SAT Encoding for Solving the Social Golfer Problem",
    RAIRO Operations Research (Equation 10).
"""

from typing import List


def encode_unique_pairings(
    g_var: List[List[List[int]]], g: int, n: int, w: int
) -> List[List[int]]:
    """
    Encode the Unique Pairings constraint (Equation 10):
    No two distinct players i < j can be in the same group in two different weeks l1 < l2.

        (~G_{i,k1,l1} | ~G_{j,k1,l1} | ~G_{i,k2,l2} | ~G_{j,k2,l2})
    """
    clauses: List[List[int]] = []
    for l1 in range(1, w):
        for l2 in range(l1 + 1, w + 1):
            for k1 in range(1, g + 1):
                row1 = g_var[l1][k1]
                for k2 in range(1, g + 1):
                    row2 = g_var[l2][k2]
                    for i in range(1, n):
                        gi1 = -row1[i]
                        gi2 = -row2[i]
                        for j in range(i + 1, n + 1):
                            clauses.append([gi1, -row1[j], gi2, -row2[j]])
    return clauses
