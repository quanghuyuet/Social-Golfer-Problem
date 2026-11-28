"""
Crash-safe CSV logger with automatic resume support for long-running benchmarks.
"""

import csv
from pathlib import Path
from typing import Dict, List, Set, Tuple

SAT_CSV_COLUMNS: List[str] = [
    "experiment",
    "instance",
    "g",
    "p",
    "w",
    "c2_encoding",
    "c1_encoding",
    "solver",
    "timeout",
    "status",
    "solve_time",
    "encode_time",
    "total_time",
    "num_vars",
    "num_clauses",
    "is_valid",
]

SATRunKey = Tuple[str, str, str, str, str]  # (experiment, instance, c2, c1, solver)


class SATCSVLogger:
    """
    Appends benchmark rows immediately to CSV and tracks completed runs for resume.
    """

    def __init__(self, csv_path: Path, overwrite: bool = False) -> None:
        self.csv_path = Path(csv_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.completed_keys: Set[SATRunKey] = set()

        if overwrite or not self.csv_path.exists() or self.csv_path.stat().st_size == 0:
            with self.csv_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=SAT_CSV_COLUMNS)
                writer.writeheader()
        else:
            self._load_existing_keys()

    def _load_existing_keys(self) -> None:
        """Read existing CSV rows so already-finished runs can be skipped on resume."""
        with self.csv_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                key: SATRunKey = (
                    row.get("experiment", ""),
                    row.get("instance", ""),
                    row.get("c2_encoding", ""),
                    row.get("c1_encoding", ""),
                    row.get("solver", ""),
                )
                self.completed_keys.add(key)

    def is_completed(
        self,
        experiment: str,
        instance: str,
        c2_encoding: str,
        c1_encoding: str,
        solver: str,
    ) -> bool:
        return (experiment, instance, c2_encoding, c1_encoding, solver) in self.completed_keys

    def log(self, row: Dict[str, object]) -> None:
        """Append one result row and flush immediately to disk."""
        full_row = {col: row.get(col, "") for col in SAT_CSV_COLUMNS}

        with self.csv_path.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SAT_CSV_COLUMNS)
            writer.writerow(full_row)
            f.flush()

        key: SATRunKey = (
            str(full_row["experiment"]),
            str(full_row["instance"]),
            str(full_row["c2_encoding"]),
            str(full_row["c1_encoding"]),
            str(full_row["solver"]),
        )
        self.completed_keys.add(key)


def load_csv_rows(csv_path: Path) -> List[Dict[str, str]]:
    """Read all rows from a benchmark CSV file."""
    path = Path(csv_path)
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))
