import csv
import os
import sys
from pathlib import Path

# Thêm thư mục gốc của dự án vào sys.path để import được module từ solvers/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from solvers.mip import cplex_mip, gurobi

# Định nghĩa các đường dẫn tương đối từ thư mục gốc dự án
DATA_PATH = PROJECT_ROOT / "dataset" / "data.txt"
RESULTS_PATH = PROJECT_ROOT / "results" / "mip" / "mip_results.csv"
TIME_LIMIT = 60  # Thời gian giới hạn mỗi bộ dữ liệu (giây)


def load_instances(filepath: Path) -> list[dict]:
    """Đọc dữ liệu từ data.txt (định dạng: g p w -> số nhóm, cỡ nhóm, số tuần)."""
    instances = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line_idx, line in enumerate(f, start=1):
            parts = line.strip().split()
            if not parts or parts[0].startswith("#"):
                continue
            if len(parts) < 3:
                continue

            g, p, w = map(int, parts[:3])
            instances.append(
                {
                    "id": line_idx,
                    "g": g,
                    "p": p,
                    "w": w,
                    "num_golfers": g * p,
                    "group_size": p,
                    "num_weeks": w,
                }
            )
    return instances


def run_single_solver(solver_module, solver_label: str, instance: dict, time_limit: int) -> dict:
    """Chạy một solver và bắt lỗi nếu vượt quá giới hạn bản quyền hoặc bộ nhớ."""
    try:
        res = solver_module.solve(instance, time_limit=time_limit)
        return {
            "solver": res.get("solver", solver_label),
            "status": res.get("status", "UNKNOWN"),
            "solve_time": res.get("solve_time", 0.0),
        }
    except Exception as e:
        error_msg = str(e).replace("\n", " ")
        status = "LICENSE_LIMIT" if "size-limited" in error_msg.lower() else f"ERROR: {error_msg}"
        return {
            "solver": solver_label,
            "status": status,
            "solve_time": 0.0,
        }


def main():
    if not DATA_PATH.exists():
        print(f"Không tìm thấy file dữ liệu tại: {DATA_PATH}")
        return

    # Tạo thư mục chứa kết quả nếu chưa tồn tại
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    instances = load_instances(DATA_PATH)
    print(f"Đã tải {len(instances)} bộ dữ liệu từ {DATA_PATH}")

    solvers = [
        ("cplex_mip", cplex_mip),
        ("gurobi_mip", gurobi),
    ]

    fieldnames = [
        "instance",
        "g",
        "p",
        "w",
        "num_golfers",
        "solver",
        "status",
        "solve_time",
    ]

    # Mở file CSV và ghi từng dòng ngay sau khi giải xong để tránh mất dữ liệu khi chạy lâu
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for inst in instances:
            inst_name = f"{inst['g']}-{inst['p']}-{inst['w']}"
            print(f"\n--- Đang giải bộ dữ liệu [{inst['id']}/{len(instances)}]: {inst_name} (n={inst['num_golfers']}) ---")

            for solver_label, solver_mod in solvers:
                result = run_single_solver(solver_mod, solver_label, inst, TIME_LIMIT)

                row = {
                    "instance": inst_name,
                    "g": inst["g"],
                    "p": inst["p"],
                    "w": inst["w"],
                    "num_golfers": inst["num_golfers"],
                    "solver": result["solver"],
                    "status": result["status"],
                    "solve_time": result["solve_time"],
                }
                writer.writerow(row)
                csvfile.flush()

                print(
                    f"  -> {result['solver']:<12} | Trạng thái: {result['status']:<15} | Thời gian: {result['solve_time']}s"
                )

    print(f"\nHoàn tất! Toàn bộ kết quả đã được lưu tại: {RESULTS_PATH}")


if __name__ == "__main__":
    main()