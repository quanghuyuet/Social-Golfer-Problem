"""
Sequential Counter encoding for At-Most-One (AMO) constraints (Constraint C1).
"""

from typing import List, Tuple
from pysat.card import CardEnc, EncType


def encode_amo_seqcounter(
    literals: List[int], top_id: int
) -> Tuple[List[List[int]], int]:
    """Encode At-Most-One (sum(literals) <= 1) using PySAT's Sequential Counter."""
    if len(literals) <= 1:
        return [], top_id
    cnf = CardEnc.atmost(lits=literals, bound=1, top_id=top_id, encoding=EncType.seqcounter)
    return list(cnf.clauses), max(top_id, cnf.nv)
