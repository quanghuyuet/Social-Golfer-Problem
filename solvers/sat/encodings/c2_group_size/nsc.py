"""
New Sequential Counter (NSC) encoding for Exactly-K constraints (Constraint C2).

Reference:
    T. V. Kieu, N. T. Nguyen, and K. V. To,
    "An Efficient SAT Encoding for Solving the Social Golfer Problem",
    RAIRO Operations Research (Equations 2-9).
"""

from typing import List, Tuple


def encode_exactly_k_nsc(
    literals: List[int], k: int, top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode sum(literals) == k using New Sequential Counter (NSC, Eq. 2-9)."""
    n = len(literals)
    clauses: List[List[int]] = []

    if k < 0 or k > n:
        return [[]], top_id
    if k == 0:
        return [[-x] for x in literals], top_id
    if k == n:
        return [[x] for x in literals], top_id

    def x(i: int) -> int:
        return literals[i - 1]

    # Auxiliary variables R_{i, j} for 1 <= i <= n-1, 1 <= j <= min(i, k)
    next_id = top_id
    r_var = {}
    for i in range(1, n):
        upper_j = min(i, k)
        for j in range(1, upper_j + 1):
            next_id += 1
            r_var[(i, j)] = next_id

    # Initialization: Eq. (2) and Eq. (3)
    for i in range(1, n):
        clauses.append([-x(i), r_var[(i, 1)]])
    for i in range(1, k + 1):
        clauses.append([x(i), -r_var[(i, i)]])

    # Sequential counter updates: Eq. (4)-(7)
    for i in range(2, n):
        upper_prev = min(i - 1, k)
        upper_curr = min(i, k)

        for j in range(1, upper_prev + 1):
            clauses.append([-r_var[(i - 1, j)], r_var[(i, j)]])            # Eq. (4)
            clauses.append([x(i), r_var[(i - 1, j)], -r_var[(i, j)]])     # Eq. (6)

        for j in range(2, upper_curr + 1):
            clauses.append([-x(i), -r_var[(i - 1, j - 1)], r_var[(i, j)]])  # Eq. (5)
            clauses.append([r_var[(i - 1, j - 1)], -r_var[(i, j)]])         # Eq. (7)

    # Final counter conditions: Eq. (8) and Eq. (9)
    if k == 1:
        clauses.append([r_var[(n - 1, 1)], x(n)])
    else:
        clauses.append([r_var[(n - 1, k)], x(n)])
        clauses.append([r_var[(n - 1, k)], r_var[(n - 1, k - 1)]])

    for i in range(k + 1, n + 1):
        clauses.append([-x(i), -r_var[(i - 1, k)]])

    return clauses, next_id
