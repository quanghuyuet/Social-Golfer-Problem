"""
Binary Decision Diagram (BDD) encoding for Exactly-K constraints (Constraint C2).
"""

from typing import List, Tuple
from pysat.pb import PBEnc, EncType


def encode_exactly_k_bdd(
    literals: List[int], k: int, top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode sum(literals) == k using BDD encoding (PySAT PBEnc via pindakaas)."""
    n = len(literals)
    if k < 0 or k > n:
        return [[]], top_id
    if k == 0:
        return [[-x] for x in literals], top_id
    if k == n:
        return [[x] for x in literals], top_id

    cnf = PBEnc.equals(
        lits=literals, bound=k, top_id=top_id, encoding=EncType.bdd
    )
    return list(cnf.clauses), max(top_id, cnf.nv)
