"""
New SAT Encoding (NSE) model for the Social Golfer Problem (SGP).

Reference:
    T. V. Kieu, N. T. Nguyen, and K. V. To,
    "An Efficient SAT Encoding for Solving the Social Golfer Problem",
    RAIRO Operations Research (Equations 1-12).
"""

import time
from pathlib import Path
from typing import Iterator, List, Optional, Tuple
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
        use_sb_pp: bool = False,
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
        self.use_sb_pp = use_sb_pp

        self.num_primary_vars = self.n * self.g * self.w
        self.top_id = self.num_primary_vars
        self.encode_time: float = 0.0
        self.num_clauses: int = 0
        self.cnf: Optional[CNF] = None

    @property
    def is_pp_p1_sb_active(self) -> bool:
        """True when specialized p-p-(p+1) symmetry breaking (Liu et al. [28]) applies."""
        return (
            self.use_sb_pp
            and self.use_sb1
            and self.use_sb2
            and self.g == self.p
            and self.w == self.p + 1
            and self.p >= 2
        )

    def var_g(self, i: int, k: int, l: int) -> int:
        """
        Return the 1-indexed Boolean variable ID for G_{ikl}:
        player i (1..n) is assigned to group k (1..g) in week l (1..w).
        """
        return ((l - 1) * self.n + (i - 1)) * self.g + k

    def _build_g_var(self) -> List[List[List[int]]]:
        """Precompute 1-indexed lookup table g_var[l][k][i]."""
        return [
            [
                [0] + [self.var_g(i, k, l) for i in range(1, self.n + 1)]
                for k in range(0, self.g + 1)
            ]
            for l in range(0, self.w + 1)
        ]

    def _build_non_c3_clauses(
        self, g_var: List[List[List[int]]]
    ) -> Tuple[List[List[int]], int]:
        """Build C1, C2, SB1, SB2, and optional SB_pp clauses and return (clauses, top_id)."""
        clauses: List[List[int]] = []
        top_id = self.num_primary_vars
        g, p, w, n = self.g, self.p, self.w, self.n
        amo_fn = AMO_ENCODERS[self.amo_encoding]
        eqk_fn = EXACTLY_K_ENCODERS[self.group_size_encoding]

        # 1. Unique Group Assignment constraint — Eq. (1)
        for l in range(1, w + 1):
            for i in range(1, n + 1):
                lits = [g_var[l][k][i] for k in range(1, g + 1)]
                clauses.extend(encode_alo(lits))
                amo_clauses, top_id = amo_fn(lits, top_id)
                clauses.extend(amo_clauses)

        # 2. Group Size constraint — Eq. (2)-(9) (or alternative Exactly-K)
        #    When SB1 is enabled, week 1 is fixed; when SB_pp is also active, week 2 is fixed.
        if self.is_pp_p1_sb_active:
            start_week = 3
        elif self.use_sb1:
            start_week = 2
        else:
            start_week = 1

        for l in range(start_week, w + 1):
            for k in range(1, g + 1):
                lits = g_var[l][k][1:]  # [G_{1kl}, ..., G_{nkl}]
                eqk_clauses, top_id = eqk_fn(lits, p, top_id)
                clauses.extend(eqk_clauses)

        # 4. Symmetry Breaking 1 (SB1) — Eq. (11): Fixed first week
        if self.use_sb1:
            for k in range(1, g + 1):
                for i in range((k - 1) * p + 1, k * p + 1):
                    clauses.append([g_var[1][k][i]])

        # 5. Symmetry Breaking 2 (SB2) — Eq. (12): Fixed first p players (l >= 2)
        if self.use_sb2:
            limit = min(g, p)
            for l in range(2, w + 1):
                for i in range(1, limit + 1):
                    clauses.append([g_var[l][i][i]])

        # 6. Specialized Symmetry Breaking for p-p-(p+1) instances (Liu et al. [28]):
        #    - Fix all of week 2 as the transpose of week 1: player (k-1)*p + m -> group m
        #    - Break week symmetry for weeks 3..p+1 by fixing group 1's partner from week-1 group 2:
        #      player p + l - 1 -> group 1 in week l (for l = 3..p+1).
        if self.is_pp_p1_sb_active:
            for k in range(2, g + 1):
                for m in range(1, p + 1):
                    player = (k - 1) * p + m
                    clauses.append([g_var[2][m][player]])
            for l in range(3, w + 1):
                clauses.append([g_var[l][1][p + l - 1]])

        return clauses, top_id

    def _iter_c3_clauses(self, g_var: List[List[List[int]]]) -> Iterator[List[int]]:
        """
        Yield Constraint C3 (Unique Pairings) clauses without materializing all in RAM.
        When SB1 / SB_pp fixes early weeks, fixed-week pairs are emitted as compact
        2-literal clauses (~G_{i,k,l} | ~G_{j,k,l}) for remaining weeks, and 4-literal
        Eq. (10) clauses are emitted for unfixed week pairs.
        """
        g, p, w, n = self.g, self.p, self.w, self.n

        if self.is_pp_p1_sb_active:
            # Weeks 1 and 2 are completely fixed:
            # - Week 1 pairs: same block of size p -> forbidden in weeks 3..w
            # - Week 2 pairs: same residue mod p   -> forbidden in weeks 3..w
            fixed_pairs = set()
            for k in range(1, g + 1):
                base = (k - 1) * p
                for a in range(1, p):
                    for b in range(a + 1, p + 1):
                        fixed_pairs.add((base + a, base + b))
            for m in range(1, p + 1):
                col = [(k - 1) * p + m for k in range(1, g + 1)]
                for idx1 in range(len(col) - 1):
                    for idx2 in range(idx1 + 1, len(col)):
                        fixed_pairs.add((col[idx1], col[idx2]))

            for l in range(3, w + 1):
                for k in range(1, g + 1):
                    row = g_var[l][k]
                    for i, j in fixed_pairs:
                        yield [-row[i], -row[j]]

            # Remaining week pairs (3 <= l1 < l2 <= w) for unfixed pairs only
            for l1 in range(3, w):
                for l2 in range(l1 + 1, w + 1):
                    for k1 in range(1, g + 1):
                        row1 = g_var[l1][k1]
                        for k2 in range(1, g + 1):
                            row2 = g_var[l2][k2]
                            for i in range(1, n):
                                gi1 = -row1[i]
                                gi2 = -row2[i]
                                for j in range(i + 1, n + 1):
                                    if (i, j) not in fixed_pairs:
                                        yield [gi1, -row1[j], gi2, -row2[j]]
        else:
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
                                    yield [gi1, -row1[j], gi2, -row2[j]]

    def build(self) -> CNF:
        """Build and return the complete CNF formula for the SGP instance."""
        t0 = time.perf_counter()
        g_var = self._build_g_var()
        clauses, top_id = self._build_non_c3_clauses(g_var)

        if self.is_pp_p1_sb_active:
            clauses.extend(self._iter_c3_clauses(g_var))
        else:
            clauses.extend(encode_unique_pairings(g_var, self.g, self.n, self.w))

        self.top_id = top_id
        self.num_clauses = len(clauses)
        cnf = CNF(from_clauses=clauses)
        if cnf.nv < top_id:
            cnf.nv = top_id

        self.cnf = cnf
        self.encode_time = time.perf_counter() - t0
        return cnf

    def write_dimacs(self, path: str) -> Tuple[int, int]:
        """
        Stream the complete CNF directly to a DIMACS file without holding all
        clauses in Python memory. Returns (num_vars, num_clauses).
        """
        t0 = time.perf_counter()
        g_var = self._build_g_var()
        non_c3_clauses, top_id = self._build_non_c3_clauses(g_var)

        self.top_id = top_id
        header_placeholder = "p cnf " + " " * 40 + "\n"
        num_clauses = len(non_c3_clauses)

        with open(path, "w", encoding="ascii", buffering=1024 * 1024) as f:
            f.write(header_placeholder)

            # Write non-C3 clauses in chunks
            buf: List[str] = []
            for cl in non_c3_clauses:
                buf.append(" ".join(str(x) for x in cl) + " 0")
                if len(buf) >= 50000:
                    f.write("\n".join(buf) + "\n")
                    buf.clear()
            if buf:
                f.write("\n".join(buf) + "\n")
                buf.clear()
            del non_c3_clauses

            # Stream C3 clauses directly
            g, p, w, n = self.g, self.p, self.w, self.n
            if self.is_pp_p1_sb_active:
                fixed_pairs = set()
                for k in range(1, g + 1):
                    base = (k - 1) * p
                    for a in range(1, p):
                        for b in range(a + 1, p + 1):
                            fixed_pairs.add((base + a, base + b))
                for m in range(1, p + 1):
                    col = [(k - 1) * p + m for k in range(1, g + 1)]
                    for idx1 in range(len(col) - 1):
                        for idx2 in range(idx1 + 1, len(col)):
                            fixed_pairs.add((col[idx1], col[idx2]))

                # Precompute unfixed pairs list for fast inner loop
                unfixed_pairs = [
                    (i, j)
                    for i in range(1, n)
                    for j in range(i + 1, n + 1)
                    if (i, j) not in fixed_pairs
                ]
                fixed_pairs_list = list(fixed_pairs)

                for l in range(3, w + 1):
                    for k in range(1, g + 1):
                        row = g_var[l][k]
                        buf = [f"{-row[i]} {-row[j]} 0" for i, j in fixed_pairs_list]
                        f.write("\n".join(buf) + "\n")
                        num_clauses += len(buf)

                for l1 in range(3, w):
                    for l2 in range(l1 + 1, w + 1):
                        for k1 in range(1, g + 1):
                            row1 = g_var[l1][k1]
                            for k2 in range(1, g + 1):
                                row2 = g_var[l2][k2]
                                buf = [
                                    f"{-row1[i]} {-row1[j]} {-row2[i]} {-row2[j]} 0"
                                    for i, j in unfixed_pairs
                                ]
                                f.write("\n".join(buf) + "\n")
                                num_clauses += len(buf)
            else:
                all_pairs = [
                    (i, j) for i in range(1, n) for j in range(i + 1, n + 1)
                ]
                for l1 in range(1, w):
                    for l2 in range(l1 + 1, w + 1):
                        for k1 in range(1, g + 1):
                            row1 = g_var[l1][k1]
                            for k2 in range(1, g + 1):
                                row2 = g_var[l2][k2]
                                buf = [
                                    f"{-row1[i]} {-row1[j]} {-row2[i]} {-row2[j]} 0"
                                    for i, j in all_pairs
                                ]
                                f.write("\n".join(buf) + "\n")
                                num_clauses += len(buf)

        # Patch the DIMACS header in-place
        header = f"p cnf {top_id} {num_clauses}"
        padded_header = header + " " * (len(header_placeholder) - 1 - len(header)) + "\n"
        with open(path, "r+", encoding="ascii") as f:
            f.seek(0)
            f.write(padded_header)

        self.num_clauses = num_clauses
        self.encode_time = time.perf_counter() - t0
        return top_id, num_clauses

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
