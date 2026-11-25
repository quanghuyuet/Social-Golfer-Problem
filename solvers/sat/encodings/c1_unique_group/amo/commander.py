"""
Commander encoding for At-Most-One (AMO) constraints (Constraint C1).

Reference:
    W. Klieber and G. Kwon, "Efficient CNF Encoding for Selecting 1 from N Objects",
    CFV 2007.
"""

from itertools import combinations
from typing import List, Tuple


def encode_amo_commander(
    literals: List[int], top_id: int, group_size: int = 3
) -> Tuple[List[List[int]], int]:
    """Encode At-Most-One (sum(literals) <= 1) using the Commander encoding."""
    n = len(literals)
    if n <= 1:
        return [], top_id

    if n <= group_size:
        clauses = [[-a, -b] for a, b in combinations(literals, 2)]
        return clauses, top_id

    clauses: List[List[int]] = []
    commanders: List[int] = []
    next_id = top_id

    for start in range(0, n, group_size):
        group = literals[start : start + group_size]
        if len(group) == 1:
            commanders.append(group[0])
            continue

        for a, b in combinations(group, 2):
            clauses.append([-a, -b])

        next_id += 1
        cmd = next_id
        commanders.append(cmd)
        for lit in group:
            clauses.append([-lit, cmd])

    rec_clauses, next_id = encode_amo_commander(commanders, next_id, group_size=group_size)
    clauses.extend(rec_clauses)
    return clauses, next_id
