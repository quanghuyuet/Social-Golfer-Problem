"""
Unified registry of SAT encodings for the Social Golfer Problem (SGP):
  - c1_unique_group/
      - alo/ -> encode_alo
      - amo/ -> AMO_ENCODERS
  - c2_group_size/      -> EXACTLY_K_ENCODERS
  - c3_unique_pairings/ -> encode_unique_pairings
"""

from typing import Callable, Dict, List, Tuple

from solvers.sat.encodings.c1_unique_group.alo.alo import encode_alo
from solvers.sat.encodings.c1_unique_group.amo.binary import encode_amo_binary
from solvers.sat.encodings.c1_unique_group.amo.commander import encode_amo_commander
from solvers.sat.encodings.c1_unique_group.amo.pairwise import encode_amo_pairwise
from solvers.sat.encodings.c1_unique_group.amo.product import encode_amo_product
from solvers.sat.encodings.c1_unique_group.amo.sequential_counter import encode_amo_seqcounter
from solvers.sat.encodings.c2_group_size.bdd import encode_exactly_k_bdd
from solvers.sat.encodings.c2_group_size.binomial import encode_exactly_k_binomial
from solvers.sat.encodings.c2_group_size.card import encode_exactly_k_card
from solvers.sat.encodings.c2_group_size.nsc import encode_exactly_k_nsc
from solvers.sat.encodings.c2_group_size.sc import encode_exactly_k_sc
from solvers.sat.encodings.c3_unique_pairings.unique_pairings import encode_unique_pairings

AMO_ENCODERS: Dict[str, Callable[[List[int], int], Tuple[List[List[int]], int]]] = {
    "pairwise": encode_amo_pairwise,
    "binary": encode_amo_binary,
    "commander": encode_amo_commander,
    "product": encode_amo_product,
    "seqcounter": encode_amo_seqcounter,
}

EXACTLY_K_ENCODERS: Dict[str, Callable[[List[int], int, int], Tuple[List[List[int]], int]]] = {
    "nsc": encode_exactly_k_nsc,
    "sc": encode_exactly_k_sc,
    "card": encode_exactly_k_card,
    "bdd": encode_exactly_k_bdd,
    "binomial": encode_exactly_k_binomial,
}

__all__ = [
    "AMO_ENCODERS",
    "EXACTLY_K_ENCODERS",
    "encode_alo",
    "encode_amo_pairwise",
    "encode_amo_binary",
    "encode_amo_commander",
    "encode_amo_product",
    "encode_amo_seqcounter",
    "encode_exactly_k_nsc",
    "encode_exactly_k_sc",
    "encode_exactly_k_card",
    "encode_exactly_k_bdd",
    "encode_exactly_k_binomial",
    "encode_unique_pairings",
]
