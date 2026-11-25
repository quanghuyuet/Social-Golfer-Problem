"""
New SAT Encoding (NSE) model for the Social Golfer Problem (SGP).

Reference:
    T. V. Kieu, N. T. Nguyen, and K. V. To,
    "An Efficient SAT Encoding for Solving the Social Golfer Problem",
    RAIRO Operations Research (Equations 1-12).
"""

import time
from typing import List, Optional
from pysat.formula import CNF

from solvers.sat.encodings import (
    AMO_ENCODERS,
    EXACTLY_K_ENCODERS,
    encode_alo,
    encode_unique_pairings,
)


class SGPModel:
    """
    SAT model for the Social Golfer Problem instance (g, p, w) using NSE.

    Attributes:
        g: Number of groups per week.
        p: Number of players per group.
        w: Number of weeks.
        n: Total number of players (g * p).
    """

    def __init__(
        self,
        g: int,
        p: int,
        w: int,
        group_size_encoding: str = "nsc",
        amo_encoding: str = "pairwise",
        use_sb1: bool = True,
        use_sb2: bool = True,
    ) -> None:
        if g < 1 or p < 1 or w < 1:
            raise ValueError(f"Invalid SGP parameters: g={g}, p={p}, w={w} (all must be >= 1).")
        if group_size_encoding not in EXACTLY_K_ENCODERS:
            raise ValueError(
                f"Unknown group_size_encoding='{group_size_encoding}'. "
                f"Available: {list(EXACTLY_K_ENCODERS.keys())}"
            )
        if amo_encoding not in AMO_ENCODERS:
            raise ValueError(
                f"Unknown amo_encoding='{amo_encoding}'. "
                f"Available: {list(AMO_ENCODERS.keys())}"
            )

        self.g = g
        self.p = p
        self.w = w
        self.n = g * p
        self.group_size_encoding = group_size_encoding
        self.amo_encoding = amo_encoding
        self.use_sb1 = use_sb1
        self.use_sb2 = use_sb2

        self.num_primary_vars = self.n * self.g * self.w
        self.top_id = self.num_primary_vars
        self.encode_time: float = 0.0
        self.cnf: Optional[CNF] = None

    def var_g(self, i: int, k: int, l: int) -> int:
        """
        Return the 1-indexed Boolean variable ID for G_{ikl}:
        player i (1..n) is assigned to group k (1..g) in week l (1..w).
        """
        return ((l - 1) * self.n + (i - 1)) * self.g + k

    def build(self) -> CNF:
        """Build and return the complete CNF formula for the SGP instance."""
        t0 = time.perf_counter()
        clauses: List[List[int]] = []
        top_id = self.num_primary_vars

        g, p, w, n = self.g, self.p, self.w, self.n
        amo_fn = AMO_ENCODERS[self.amo_encoding]
        eqk_fn = EXACTLY_K_ENCODERS[self.group_size_encoding]

        # Precompute lookup table g_var[l][k][i] (1-indexed) for fast clause generation
        g_var = [
            [
                [0] + [self.var_g(i, k, l) for i in range(1, n + 1)]
                for k in range(0, g + 1)
            ]
            for l in range(0, w + 1)
        ]

        # ------------------------------------------------------------------
        # 1. Unique Group Assignment constraint — Eq. (1)
        #    For each player i and week l: sum_{k=1..g} G_{ikl} == 1
        # ------------------------------------------------------------------
        for l in range(1, w + 1):
            for i in range(1, n + 1):
                lits = [g_var[l][k][i] for k in range(1, g + 1)]
                # ALO: player i must be in at least one group
                clauses.extend(encode_alo(lits))
                # AMO: player i can be in at most one group
                amo_clauses, top_id = amo_fn(lits, top_id)
                clauses.extend(amo_clauses)

        # ------------------------------------------------------------------
        # 2. Group Size constraint — Eq. (2)-(9) (or alternative Exactly-K)
        #    For each group k and week l: sum_{i=1..n} G_{ikl} == p
        #    Note: When SB1 is enabled, week 1 assignments are fixed by SB1 + C1,
        #    so Group Size constraints are only needed for weeks 2..w.
        # ------------------------------------------------------------------
        start_week = 2 if self.use_sb1 else 1
        for l in range(start_week, w + 1):
            for k in range(1, g + 1):
                lits = g_var[l][k][1:]  # [G_{1kl}, ..., G_{nkl}]
                eqk_clauses, top_id = eqk_fn(lits, p, top_id)
                clauses.extend(eqk_clauses)

        # ------------------------------------------------------------------
        # 3. Unique Pairings constraint — Eq. (10)
        #    No two distinct players i < j play in the same group in two weeks l1 < l2
        # ------------------------------------------------------------------
        clauses.extend(encode_unique_pairings(g_var, g, n, w))

        # ------------------------------------------------------------------
        # 4. Symmetry Breaking 1 (SB1) — Eq. (11): Fixed first week
        # ------------------------------------------------------------------
        if self.use_sb1:
            for k in range(1, g + 1):
                for i in range((k - 1) * p + 1, k * p + 1):
                    clauses.append([g_var[1][k][i]])

        # ------------------------------------------------------------------
        # 5. Symmetry Breaking 2 (SB2) — Eq. (12): Fixed first p players (l >= 2)
        # ------------------------------------------------------------------
        if self.use_sb2:
            limit = min(g, p)
            for l in range(2, w + 1):
                for i in range(1, limit + 1):
                    clauses.append([g_var[l][i][i]])

        self.top_id = top_id
        cnf = CNF(from_clauses=clauses)
        # Ensure nv reflects the total allocated variable count
        if cnf.nv < top_id:
            cnf.nv = top_id

        self.cnf = cnf
        self.encode_time = time.perf_counter() - t0
        return cnf

    def decode_solution(self, model: List[int]) -> List[List[List[int]]]:
        """
        Decode a SAT model (list of signed integer literals) into an SGP schedule.

        Returns:
            schedule: list of weeks (length w), where each week is a list of groups
            (length g), and each group is a sorted list of 1-indexed player IDs.
        """
        true_vars = {lit for lit in model if lit > 0 and lit <= self.num_primary_vars}
        schedule: List[List[List[int]]] = []
        for l in range(1, self.w + 1):
            week_groups: List[List[int]] = []
            for k in range(1, self.g + 1):
                group = [
                    i for i in range(1, self.n + 1)
                    if self.var_g(i, k, l) in true_vars
                ]
                week_groups.append(group)
            schedule.append(week_groups)
        return schedule

    @staticmethod
    def format_schedule(schedule: List[List[List[int]]]) -> str:
        """Format a decoded schedule into a human-readable string."""
        lines = []
        for w_idx, week in enumerate(schedule, start=1):
            groups_str = "  ".join(
                "{" + ", ".join(str(p) for p in grp) + "}" for grp in week
            )
            lines.append(f"Week {w_idx:2d}: {groups_str}")
        return "\n".join(lines)
