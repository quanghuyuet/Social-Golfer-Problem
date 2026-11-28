"""
Focused SAT Benchmark for the 7 specialized p-p-(p+1) instances
using NSE_NSC with p-p-(p+1) symmetry breaking (SB1 + SB2 + SB_pp, Liu et al. [28])
and low-memory streaming CNF generation.

Results are written to a separate CSV (results/sat/pp_p1_sb_results.csv) with the
exact same schema as results/sat/encoding_results.csv so the original benchmark
data remains untouched and can be compared or merged later.

Usage:
    python -m benchmark.benchmark_pp_p1 --timeout 180
"""

import argparse
import math
from pathlib import Path
from typing import List, Tuple

from benchmark.csv_log import SATCSVLogger
from solvers.sat.solver import solve_sgp

DEFAULT_MAX_BINO_CLAUSES = 10_000_000


def estimate_binomial_c2_clauses(g: int, p: int, w: int) -> int:
    """Estimate number of C2 clauses for Binomial encoding with SB_pp (weeks 3..w)."""
    n = g * p
    c2_weeks = max(0, w - 2)
    return c2_weeks * g * (math.comb(n, n - p + 1) + math.comb(n, p + 1))

PP_P1_INSTANCES: List[Tuple[int, int, int]] = [
    (5, 5, 6),
    (6, 6, 7),
    (7, 7, 8),
    (8, 8, 9),
    (9, 9, 10),
    (11, 11, 12),
    (13, 13, 14),
]

DEFAULT_OUTPUT_PATH = Path("results/sat/pp_p1_sb_results.csv")


def run_benchmark(
    timeout: float = 180.0,
    solvers: List[str] = None,
    c2_encodings: List[str] = None,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    overwrite: bool = False,
) -> None:
    if solvers is None:
        solvers = ["kissat", "glucose3"]
    if c2_encodings is None:
        c2_encodings = ["nsc"]

    logger = SATCSVLogger(output_path, overwrite=overwrite)

    for solver_name in solvers:
        experiment = "c2_exactly_k" if solver_name == "kissat" else "cross_solver"
        for c2 in c2_encodings:
            for g, p, w in PP_P1_INSTANCES:
                inst_name = f"{g}-{p}-{w}"
                if logger.is_completed(experiment, inst_name, c2, "pairwise", solver_name):
                    print(f"[SKIP] {inst_name} | {c2} | {solver_name} (already logged)")
                    continue

                if c2 == "binomial":
                    est_c2 = estimate_binomial_c2_clauses(g, p, w)
                    if est_c2 > DEFAULT_MAX_BINO_CLAUSES:
                        n_vars = g * p * g * w
                        row = {
                            "experiment": experiment,
                            "instance": inst_name,
                            "g": g,
                            "p": p,
                            "w": w,
                            "c2_encoding": c2,
                            "c1_encoding": "pairwise",
                            "solver": solver_name,
                            "timeout": timeout,
                            "status": "MEMOUT",
                            "solve_time": "",
                            "encode_time": "",
                            "total_time": "",
                            "num_vars": n_vars,
                            "num_clauses": est_c2,
                            "is_valid": "",
                        }
                        logger.log(row)
                        print(
                            f"[SKIP] {inst_name} | binomial | {solver_name} -> MEMOUT "
                            f"(estimated C2 clauses={est_c2:,} > {DEFAULT_MAX_BINO_CLAUSES:,})",
                            flush=True,
                        )
                        continue

                print(f"[RUN ] {inst_name} | {c2} | {solver_name} | timeout={timeout}s ...", flush=True)
                try:
                    res = solve_sgp(
                        g=g,
                        p=p,
                        w=w,
                        group_size_encoding=c2,
                        amo_encoding="pairwise",
                        solver_name=solver_name,
                        timeout=timeout,
                        use_sb1=True,
                        use_sb2=True,
                        use_sb_pp=True,
                        verify=True,
                    )
                    total_time = res.solve_time + res.encode_time
                    row = {
                        "experiment": experiment,
                        "instance": inst_name,
                        "g": g,
                        "p": p,
                        "w": w,
                        "c2_encoding": c2,
                        "c1_encoding": "pairwise",
                        "solver": solver_name,
                        "timeout": timeout,
                        "status": res.status,
                        "solve_time": f"{res.solve_time:.4f}",
                        "encode_time": f"{res.encode_time:.4f}",
                        "total_time": f"{total_time:.4f}",
                        "num_vars": res.num_vars,
                        "num_clauses": res.num_clauses,
                        "is_valid": "" if res.is_valid is None else str(res.is_valid),
                    }
                    print(
                        f"[DONE] {inst_name} | {c2} | {solver_name} -> {res.status} "
                        f"(solve={res.solve_time:.3f}s, enc={res.encode_time:.3f}s, "
                        f"vars={res.num_vars}, cls={res.num_clauses}, valid={res.is_valid})",
                        flush=True,
                    )
                except MemoryError:
                    row = {
                        "experiment": experiment,
                        "instance": inst_name,
                        "g": g,
                        "p": p,
                        "w": w,
                        "c2_encoding": c2,
                        "c1_encoding": "pairwise",
                        "solver": solver_name,
                        "timeout": timeout,
                        "status": "MEMOUT",
                        "solve_time": "",
                        "encode_time": "",
                        "total_time": "",
                        "num_vars": "",
                        "num_clauses": "",
                        "is_valid": "",
                    }
                    print(f"[DONE] {inst_name} | {c2} | {solver_name} -> MEMOUT", flush=True)
                except Exception as exc:
                    row = {
                        "experiment": experiment,
                        "instance": inst_name,
                        "g": g,
                        "p": p,
                        "w": w,
                        "c2_encoding": c2,
                        "c1_encoding": "pairwise",
                        "solver": solver_name,
                        "timeout": timeout,
                        "status": "ERROR",
                        "solve_time": "",
                        "encode_time": "",
                        "total_time": "",
                        "num_vars": "",
                        "num_clauses": "",
                        "is_valid": "",
                    }
                    print(f"[ERR ] {inst_name} | {c2} | {solver_name} -> {exc}", flush=True)

                logger.log(row)


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark 7 p-p-(p+1) SGP instances with SB_pp.")
    parser.add_argument("--timeout", type=float, default=180.0, help="Timeout per run (seconds).")
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=["kissat", "glucose3"],
        help="SAT solvers to run (default: kissat glucose3).",
    )
    parser.add_argument(
        "--c2",
        nargs="+",
        default=["nsc"],
        help="C2 encodings to run (default: nsc).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output CSV path.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing output CSV.")
    args = parser.parse_args()

    run_benchmark(
        timeout=args.timeout,
        solvers=args.solvers,
        c2_encodings=args.c2,
        output_path=args.output,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
