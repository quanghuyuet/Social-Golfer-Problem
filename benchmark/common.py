"""
Shared utilities and benchmark definitions for SAT, CP, and MIP experiments.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATH = PROJECT_ROOT / "dataset" / "data.txt"
DEFAULT_SAT_RESULTS_PATH = PROJECT_ROOT / "results" / "sat" / "encoding_results.csv"

# Paper experimental time limit: 900 seconds (15 minutes)
PAPER_TIMEOUT_SECONDS = 900.0

# Representative 15 instances from dataset/data.txt for Axis 2 (C1 AMO comparison)
# Spans small/medium/hard SAT & UNSAT and diverse group counts (g = 3..15)
AXIS2_REPRESENTATIVE_INSTANCES = [
    "3-2-2",
    "4-3-3",
    "5-3-5",
    "5-3-7",
    "5-4-4",
    "5-5-6",
    "5-8-3",
    "6-6-3",
    "6-7-4",
    "7-7-3",
    "8-4-6",
    "8-4-7",
    "9-4-6",
    "10-9-3",
    "15-8-2",
]

# 6 medium/challenging instances for Interaction Check (Top 3 C2 x 5 C1)
INTERACTION_CHECK_INSTANCES = [
    "5-3-7",
    "5-5-6",
    "6-6-3",
    "7-7-3",
    "8-4-6",
    "9-4-6",
]


@dataclass(frozen=True)
class SGPInstance:
    """Represents one Social Golfer Problem instance (g, p, w)."""

    g: int
    p: int
    w: int

    @property
    def n(self) -> int:
        return self.g * self.p

    @property
    def name(self) -> str:
        return f"{self.g}-{self.p}-{self.w}"

    @property
    def primary_vars(self) -> int:
        return self.n * self.g * self.w


def parse_instance_line(line: str) -> Optional[SGPInstance]:
    """Parse a single line in 'g p w' or 'g-p-w' format."""
    cleaned = line.strip()
    if not cleaned or cleaned.startswith("#"):
        return None
    normalized = cleaned.replace("-", " ").replace(",", " ")
    parts = normalized.split()
    if len(parts) != 3:
        raise ValueError(f"Invalid SGP instance line: '{line.strip()}'")
    g, p, w = int(parts[0]), int(parts[1]), int(parts[2])
    return SGPInstance(g=g, p=p, w=w)


def load_instances(
    path: Optional[Path] = None,
    sort_by_size: bool = False,
) -> List[SGPInstance]:
    """
    Load SGP instances from dataset/data.txt (preserving unique instances).

    Args:
        path: Path to dataset file. Defaults to dataset/data.txt.
        sort_by_size: If True, sort instances ascending by primary_vars (g*p*g*w).
    """
    dataset_path = Path(path) if path is not None else DEFAULT_DATASET_PATH
    if not dataset_path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    instances: List[SGPInstance] = []
    seen = set()
    with dataset_path.open("r", encoding="utf-8") as f:
        for line in f:
            inst = parse_instance_line(line)
            if inst is not None and inst.name not in seen:
                seen.add(inst.name)
                instances.append(inst)

    if sort_by_size:
        instances.sort(key=lambda x: (x.primary_vars, x.g, x.p, x.w))

    return instances
