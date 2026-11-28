"""
SAT Benchmark Runner for the Social Golfer Problem (SGP).

Supports 4 structured experiment suites (default timeout = 900s, matching Kieu et al.):
  1. c2           : Axis 1 — Compare 5 C2 (Group Size) encodings (nsc, sc, card, bdd, binomial)
                    with C1=pairwise, solver=kissat across all instances in dataset/data.txt.
  2. c1           : Axis 2 — Compare 5 C1 (AMO) encodings (pairwise, binary, commander, product, seqcounter)
                    with C2=nsc, solver=kissat across 15 representative instances.
  3. interaction  : Interaction check — Top 3 C2 (nsc, card, bdd) x 5 C1 on 6 representative instances.
  4. cross_solver : Cross-solver check — NSE_NSC with glucose3 across dataset/data.txt.

Results are flushed immediately to results/sat/encoding_results.csv and automatically
resumed on restart.

Examples:
    python -m benchmark.benchmark_sat --experiment c2 --timeout 900
    python -m benchmark.benchmark_sat --experiment c1 --timeout 900
    python -m benchmark.benchmark_sat --experiment interaction --timeout 900
    python -m benchmark.benchmark_sat --experiment all --timeout 900
"""

import argparse
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from benchmark.common import (
    AXIS2_REPRESENTATIVE_INSTANCES,
    DEFAULT_DATASET_PATH,
    DEFAULT_SAT_RESULTS_PATH,
    DEFAULT_TIMEOUT_SECONDS,
    INTERACTION_CHECK_INSTANCES,
    SGPInstance,
    load_instances,
)
from benchmark.csv_log import SATCSVLogger
from solvers.sat.encodings import AMO_ENCODERS, EXACTLY_K_ENCODERS
from solvers.sat.solver import solve_sgp

ALL_C2_ENCODINGS = ["nsc", "sc", "card", "bdd", "binomial"]
ALL_C1_ENCODINGS = ["pairwise", "binary", "commander", "product", "seqcounter"]
TOP3_C2_ENCODINGS = ["nsc", "card", "bdd"]

# Safety cap for Binomial C2 clauses to prevent RAM exhaustion on large instances
DEFAULT_MAX_BINO_CLAUSES = 10_000_000


def estimate_binomial_total_clauses(inst: SGPInstance, use_sb1: bool = True) -> int:
    """Compute exact clause count for NSE_BINO (C1 pairwise + C2 binomial + C3 + SB1/SB2)."""
    g, p, w, n = inst.g, inst.p, inst.w, inst.n
    c1 = n * w * (1 + math.comb(g, 2))
    c2_weeks = (w - 1) if use_sb1 else w
    c2_per_group = math.comb(n, n - p + 1) + math.comb(n, p + 1)
    c2 = c2_weeks * g * c2_per_group
    c3 = math.comb(w, 2) * g * g * math.comb(n, 2)
    sb1 = n if use_sb1 else 0
    sb2 = max(0, w - 1) * min(g, p)
    return c1 + c2 + c3 + sb1 + sb2


def build_task_list(
    experiment: str,
    all_instances: List[SGPInstance],
    c2_filter: Optional[List[str]] = None,
    c1_filter: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> List[Tuple[str, SGPInstance, str, str, str]]:
    """
    Build the ordered list of benchmark tasks:
        (experiment_name, instance, c2_encoding, c1_encoding, solver_name)
    """
    inst_by_name: Dict[str, SGPInstance] = {inst.name: inst for inst in all_instances}
    tasks: List[Tuple[str, SGPInstance, str, str, str]] = []

    c2_list = c2_filter if c2_filter else ALL_C2_ENCODINGS
    c1_list = c1_filter if c1_filter else ALL_C1_ENCODINGS

    def _subset_by_names(names: List[str]) -> List[SGPInstance]:
        selected = [inst_by_name[nm] for nm in names if nm in inst_by_name]
        return selected[:limit] if limit is not None else selected

    base_instances = all_instances[:limit] if limit is not None else all_instances

    if experiment in ("c2", "all"):
        c2_amo_list = c1_filter if (experiment == "c2" and c1_filter) else ["pairwise"]
        for inst in base_instances:
            for c2 in c2_list:
                for c1 in c2_amo_list:
                    tasks.append(("c2_exactly_k", inst, c2, c1, "kissat"))

    if experiment in ("c1", "all"):
        rep_instances = _subset_by_names(AXIS2_REPRESENTATIVE_INSTANCES)
        for inst in rep_instances:
            for c1 in c1_list:
                tasks.append(("c1_amo", inst, "nsc", c1, "kissat"))

    if experiment in ("interaction", "all"):
        inter_instances = _subset_by_names(INTERACTION_CHECK_INSTANCES)
        inter_c2 = [c for c in TOP3_C2_ENCODINGS if c in c2_list]
        for inst in inter_instances:
            for c2 in inter_c2:
                for c1 in c1_list:
                    tasks.append(("interaction", inst, c2, c1, "kissat"))

    if experiment in ("cross_solver", "all"):
        for inst in base_instances:
            tasks.append(("cross_solver", inst, "nsc", "pairwise", "glucose3"))

    return tasks


def run_benchmark(
    experiment: str = "c2",
    dataset_path: Path = DEFAULT_DATASET_PATH,
    output_csv: Path = DEFAULT_SAT_RESULTS_PATH,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bino_clauses: int = DEFAULT_MAX_BINO_CLAUSES,
    sort_by_size: bool = True,
    overwrite: bool = False,
    limit: Optional[int] = None,
    c2_filter: Optional[List[str]] = None,
    c1_filter: Optional[List[str]] = None,
    verbose: bool = True,
) -> int:
    """Execute SAT benchmark tasks and log every result immediately to CSV."""
    instances = load_instances(dataset_path, sort_by_size=sort_by_size)
    tasks = build_task_list(
        experiment=experiment,
        all_instances=instances,
        c2_filter=c2_filter,
        c1_filter=c1_filter,
        limit=limit,
    )
    logger = SATCSVLogger(output_csv, overwrite=overwrite)

    total_tasks = len(tasks)
    executed = 0
    skipped = 0

    if verbose:
        already_done = sum(
            1
            for (exp_name, inst, c2, c1, solver_name) in tasks
            if logger.is_completed(exp_name, inst.name, c2, c1, solver_name)
        )
        print(
            f"=== SAT Benchmark [{experiment}] | tasks={total_tasks} | "
            f"resumed={already_done} | remaining={total_tasks - already_done} | "
            f"timeout={timeout}s | output={output_csv} ===",
            flush=True,
        )

    for idx, (exp_name, inst, c2, c1, solver_name) in enumerate(tasks, start=1):
        if logger.is_completed(exp_name, inst.name, c2, c1, solver_name):
            skipped += 1
            continue

        prefix = (
            f"[{idx:3d}/{total_tasks}] {exp_name:12s} | {inst.name:8s} | "
            f"C2={c2:8s} C1={c1:10s} | {solver_name:8s}"
        )

        # Pre-check Binomial clause explosion to avoid RAM exhaustion
        if c2 == "binomial":
            est_clauses = estimate_binomial_total_clauses(inst, use_sb1=True)
            if est_clauses > max_bino_clauses:
                logger.log(
                    {
                        "experiment": exp_name,
                        "instance": inst.name,
                        "g": inst.g,
                        "p": inst.p,
                        "w": inst.w,
                        "c2_encoding": c2,
                        "c1_encoding": c1,
                        "solver": solver_name,
                        "timeout": timeout,
                        "status": "MEMOUT",
                        "solve_time": "",
                        "encode_time": "",
                        "total_time": "",
                        "num_vars": inst.primary_vars,
                        "num_clauses": est_clauses,
                        "is_valid": "",
                    }
                )
                executed += 1
                if verbose:
                    print(
                        f"{prefix} -> MEMOUT (est clauses={est_clauses:.2e})",
                        flush=True,
                    )
                continue

        if verbose:
            print(f"{prefix} ... ", end="", flush=True)

        try:
            res = solve_sgp(
                g=inst.g,
                p=inst.p,
                w=inst.w,
                group_size_encoding=c2,
                amo_encoding=c1,
                solver_name=solver_name,
                timeout=timeout,
                use_sb1=True,
                use_sb2=True,
                verify=True,
            )
            total_time = res.encode_time + res.solve_time
            logger.log(
                {
                    "experiment": exp_name,
                    "instance": inst.name,
                    "g": inst.g,
                    "p": inst.p,
                    "w": inst.w,
                    "c2_encoding": c2,
                    "c1_encoding": c1,
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
            )
            executed += 1
            if verbose:
                valid_tag = (
                    " [VALID]"
                    if res.is_valid is True
                    else (" [INVALID!]" if res.is_valid is False else "")
                )
                print(
                    f"-> {res.status:7s} solve={res.solve_time:7.3f}s "
                    f"vars={res.num_vars:,} cls={res.num_clauses:,}{valid_tag}",
                    flush=True,
                )
        except MemoryError:
            logger.log(
                {
                    "experiment": exp_name,
                    "instance": inst.name,
                    "g": inst.g,
                    "p": inst.p,
                    "w": inst.w,
                    "c2_encoding": c2,
                    "c1_encoding": c1,
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
            )
            executed += 1
            if verbose:
                print("-> MEMOUT (MemoryError)", flush=True)

    if verbose:
        print(f"=== Done: executed={executed}, skipped(resumed)={skipped}, total={total_tasks} ===")
    return executed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAT benchmarks for SGP.")
    parser.add_argument(
        "--experiment",
        choices=["c2", "c1", "interaction", "cross_solver", "all"],
        default="c2",
        help="Which experiment suite to run. Default: c2",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET_PATH,
        help="Path to dataset file. Default: dataset/data.txt",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_SAT_RESULTS_PATH,
        help="Output CSV path. Default: results/sat/encoding_results.csv",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Time limit per instance in seconds. Default: 60.0",
    )
    parser.add_argument(
        "--max-bino-clauses",
        type=int,
        default=DEFAULT_MAX_BINO_CLAUSES,
        help="Max estimated clauses for Binomial before logging MEMOUT. Default: 10000000",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help="Keep dataset file order instead of sorting ascending by problem size",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing CSV instead of resuming from previous progress",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of instances (useful for quick smoke tests)",
    )
    parser.add_argument(
        "--c2",
        nargs="+",
        choices=list(EXACTLY_K_ENCODERS.keys()),
        default=None,
        help="Optional subset of C2 encodings to run",
    )
    parser.add_argument(
        "--c1",
        nargs="+",
        choices=list(AMO_ENCODERS.keys()),
        default=None,
        help="Optional subset of C1 encodings to run",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_benchmark(
        experiment=args.experiment,
        dataset_path=args.dataset,
        output_csv=args.output,
        timeout=args.timeout,
        max_bino_clauses=args.max_bino_clauses,
        sort_by_size=not args.no_sort,
        overwrite=args.overwrite,
        limit=args.limit,
        c2_filter=args.c2,
        c1_filter=args.c1,
        verbose=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
