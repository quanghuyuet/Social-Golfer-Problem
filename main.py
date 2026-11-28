"""
CLI entry point to solve a single Social Golfer Problem (g, p, w) instance using SAT.

Example:
    python main.py 5 3 7 --c2 nsc --c1 pairwise --solver kissat --timeout 60
"""

import argparse
import sys

from solvers.sat.encodings import AMO_ENCODERS, EXACTLY_K_ENCODERS
from solvers.sat.model import SGPModel
from solvers.sat.solver import solve_sgp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Solve a Social Golfer Problem instance (g-p-w) using SAT encoding."
    )
    parser.add_argument("g", type=int, help="Number of groups per week")
    parser.add_argument("p", type=int, help="Number of players per group")
    parser.add_argument("w", type=int, help="Number of weeks")
    parser.add_argument(
        "--c2",
        "--group-size-encoding",
        dest="c2",
        default="nsc",
        choices=list(EXACTLY_K_ENCODERS.keys()),
        help="Exactly-K encoding for Constraint C2 (Group Size). Default: nsc",
    )
    parser.add_argument(
        "--c1",
        "--amo-encoding",
        dest="c1",
        default="pairwise",
        choices=list(AMO_ENCODERS.keys()),
        help="AMO encoding for Constraint C1 (Unique Group Assignment). Default: pairwise",
    )
    parser.add_argument(
        "--solver",
        default="kissat",
        help="SAT solver name ('kissat', 'glucose3', 'cadical195', ...). Default: kissat",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Solver time limit in seconds. Default: 60.0",
    )
    parser.add_argument(
        "--no-sb1",
        action="store_true",
        help="Disable Symmetry Breaking 1 (Fixed first week)",
    )
    parser.add_argument(
        "--no-sb2",
        action="store_true",
        help="Disable Symmetry Breaking 2 (Fixed first p players)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print(
        f"Solving SGP {args.g}-{args.p}-{args.w} "
        f"[C2={args.c2}, C1={args.c1}, solver={args.solver}, timeout={args.timeout}s]"
    )

    res = solve_sgp(
        g=args.g,
        p=args.p,
        w=args.w,
        group_size_encoding=args.c2,
        amo_encoding=args.c1,
        solver_name=args.solver,
        timeout=args.timeout,
        use_sb1=not args.no_sb1,
        use_sb2=not args.no_sb2,
        verify=True,
    )

    print("-" * 60)
    print(f"Status      : {res.status}")
    print(f"Encode time : {res.encode_time:.4f} s")
    print(f"Solve time  : {res.solve_time:.4f} s")
    print(f"Variables   : {res.num_vars:,}")
    print(f"Clauses     : {res.num_clauses:,}")

    if res.status == "SAT" and res.schedule is not None:
        print(f"Verified    : {'VALID' if res.is_valid else 'INVALID (' + str(res.error_message) + ')'}")
        print("-" * 60)
        print(SGPModel.format_schedule(res.schedule))
        return 0 if res.is_valid else 2
    if res.status == "UNSAT":
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
