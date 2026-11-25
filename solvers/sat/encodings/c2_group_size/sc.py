"""
Sinz's Sequential Counter (SC) encoding for Exactly-K constraints (Constraint C2).
"""

from typing import List, Tuple
from pysat.card import CardEnc, EncType


def encode_exactly_k_sc(
    literals: List[int], k: int, top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode sum(literals) == k using Sinz's Sequential Counter (PySAT)."""
    n = len(literals)
    if k < 0 or k > n:
        return [[]], top_id
    if k == 0:
        return [[-x] for x in literals], top_id
    if k == n:
        return [[x] for x in literals], top_id

    cnf = CardEnc.equals(
        lits=literals, bound=k, top_id=top_id, encoding=EncType.seqcounter
    )
    return list(cnf.clauses), max(top_id, cnf.nv)
