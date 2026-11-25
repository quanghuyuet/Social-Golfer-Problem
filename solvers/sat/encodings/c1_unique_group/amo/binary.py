"""
Binary (Bitwise) encoding for At-Most-One (AMO) constraints (Constraint C1).
"""

from typing import List, Tuple
from pysat.card import CardEnc, EncType


def encode_amo_binary(
    literals: List[int], top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode At-Most-One (sum(literals) <= 1) using PySAT's Bitwise encoding."""
    if len(literals) <= 1:
        return [], top_id
    cnf = CardEnc.atmost(lits=literals, bound=1, top_id=top_id, encoding=EncType.bitwise)
    return list(cnf.clauses), max(top_id, cnf.nv)
