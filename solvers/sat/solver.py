"""
SAT Solver wrappers (Kissat CLI & PySAT solvers) and high-level SGP solve API.
"""

import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from pysat.formula import CNF
from pysat.solvers import Solver as PySATBackend

from benchmark.verify import verify_schedule
from solvers.sat.model import SGPModel

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KISSAT_PATHS = [
    PROJECT_ROOT / "tools" / "kissat" / "build" / "kissat.exe",
    PROJECT_ROOT / "tools" / "kissat" / "build" / "kissat",
]


@dataclass
class SolveResult:
    """Standardized result object for solving an SGP instance."""

    g: int
    p: int
    w: int
    status: str  # "SAT", "UNSAT", "TIMEOUT", "ERROR"
    solve_time: float
    encode_time: float
    num_vars: int
    num_clauses: int
    solver_name: str
    group_size_encoding: str
    amo_encoding: str
    schedule: Optional[List[List[List[int]]]] = None
    is_valid: Optional[bool] = None
    error_message: Optional[str] = None


def find_kissat_binary(kissat_path: Optional[str] = None) -> str:
    """Locate the Kissat executable."""
    if kissat_path:
        if os.path.isfile(kissat_path):
            return kissat_path
        raise FileNotFoundError(f"Kissat binary not found at: {kissat_path}")

    for candidate in DEFAULT_KISSAT_PATHS:
        if candidate.is_file():
            return str(candidate)

    in_path = shutil.which("kissat")
    if in_path:
        return in_path

    raise FileNotFoundError(
        "Kissat binary not found. Expected at tools/kissat/build/kissat.exe or in PATH."
    )


class KissatSolver:
    """Wrapper to invoke the Kissat SAT solver via DIMACS CNF files."""

    def __init__(self, binary_path: Optional[str] = None) -> None:
        self.binary_path = find_kissat_binary(binary_path)

    def solve(
        self, cnf: CNF, timeout: Optional[float] = 900.0
    ) -> Tuple[str, Optional[List[int]], float]:
        """
        Solve a PySAT CNF object using Kissat.

        Returns:
            (status, model, solve_time_seconds)
            status is one of: "SAT", "UNSAT", "TIMEOUT", "ERROR".
        """
        tmp_fd, cnf_path = tempfile.mkstemp(suffix=".cnf", prefix="sgp_")
        os.close(tmp_fd)
        try:
            cnf.to_file(cnf_path)
            cmd = [self.binary_path, cnf_path]
            if timeout is not None:
                # Pass Kissat's internal --time limit as integer ceiling,
                # and also enforce a slightly larger subprocess timeout as safety net.
                cmd.insert(1, f"--time={max(1, int(timeout))}")

            t0 = time.perf_counter()
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=(timeout + 5.0) if timeout is not None else None,
                )
            except subprocess.TimeoutExpired:
                wall_time = time.perf_counter() - t0
                return "TIMEOUT", None, wall_time

            wall_time = time.perf_counter() - t0
            return self._parse_output(proc.stdout, proc.returncode, wall_time)
        finally:
            if os.path.exists(cnf_path):
                try:
                    os.remove(cnf_path)
                except OSError:
                    pass

    @staticmethod
    def _parse_output(
        stdout: str, returncode: int, wall_time: float
    ) -> Tuple[str, Optional[List[int]], float]:
        """Parse Kissat standard output for status, model literals, and CPU time."""
        status = "UNKNOWN"
        model: List[int] = []
        process_time: Optional[float] = None

        time_pattern = re.compile(r"c\s+process-time:.*?([0-9]+(?:\.[0-9]+)?)\s+seconds")

        for line in stdout.splitlines():
            if line.startswith("s "):
                if "UNSATISFIABLE" in line:
                    status = "UNSAT"
                elif "SATISFIABLE" in line:
                    status = "SAT"
                elif "UNKNOWN" in line:
                    status = "TIMEOUT"
            elif line.startswith("v "):
                for tok in line[2:].split():
                    val = int(tok)
                    if val != 0:
                        model.append(val)
            elif "process-time:" in line:
                m = time_pattern.search(line)
                if m:
                    process_time = float(m.group(1))

        if status == "UNKNOWN":
            if returncode == 10:
                status = "SAT"
            elif returncode == 20:
                status = "UNSAT"
            elif returncode == 0:
                status = "TIMEOUT"
            else:
                status = "ERROR"

        elapsed = process_time if process_time is not None else wall_time
        return status, (model if status == "SAT" else None), elapsed


class PySATSolver:
    """Wrapper for built-in PySAT solvers (e.g., glucose3, cadical195)."""

    def __init__(self, name: str = "glucose3") -> None:
        self.name = name

    def solve(
        self, cnf: CNF, timeout: Optional[float] = 900.0
    ) -> Tuple[str, Optional[List[int]], float]:
        """Solve a CNF using a PySAT backend solver with interrupt-based timeout."""
        t0 = time.perf_counter()
        with PySATBackend(name=self.name, bootstrap_with=cnf.clauses) as solver:
            timer: Optional[threading.Timer] = None
            if timeout is not None:
                timer = threading.Timer(timeout, solver.interrupt)
                timer.start()
            try:
                res = solver.solve_limited(expect_interrupt=True)
            finally:
                if timer is not None:
                    timer.cancel()

            elapsed = time.perf_counter() - t0
            if res is True:
                return "SAT", solver.get_model(), elapsed
            if res is False:
                return "UNSAT", None, elapsed
            return "TIMEOUT", None, elapsed


def solve_sgp(
    g: int,
    p: int,
    w: int,
    group_size_encoding: str = "nsc",
    amo_encoding: str = "pairwise",
    solver_name: str = "kissat",
    timeout: Optional[float] = 900.0,
    use_sb1: bool = True,
    use_sb2: bool = True,
    verify: bool = True,
    kissat_path: Optional[str] = None,
) -> SolveResult:
    """
    Build the SAT model for SGP (g, p, w), solve it, decode and verify the schedule.
    """
    sgp_model = SGPModel(
        g=g,
        p=p,
        w=w,
        group_size_encoding=group_size_encoding,
        amo_encoding=amo_encoding,
        use_sb1=use_sb1,
        use_sb2=use_sb2,
    )
    cnf = sgp_model.build()

    if solver_name.lower() == "kissat":
        solver = KissatSolver(binary_path=kissat_path)
    else:
        solver = PySATSolver(name=solver_name)

    status, model, solve_time = solver.solve(cnf, timeout=timeout)

    schedule = None
    is_valid = None
    error_message = None

    if status == "SAT" and model is not None:
        schedule = sgp_model.decode_solution(model)
        if verify:
            ok, msg = verify_schedule(g, p, w, schedule)
            is_valid = ok
            if not ok:
                error_message = msg

    return SolveResult(
        g=g,
        p=p,
        w=w,
        status=status,
        solve_time=solve_time,
        encode_time=sgp_model.encode_time,
        num_vars=cnf.nv,
        num_clauses=len(cnf.clauses),
        solver_name=solver_name,
        group_size_encoding=group_size_encoding,
        amo_encoding=amo_encoding,
        schedule=schedule,
        is_valid=is_valid,
        error_message=error_message,
    )
