import csv
from pathlib import Path

# Xác định thư mục gốc của dự án (Social-Golfer-Problem)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Đường dẫn tới các file đầu vào và đầu ra
SAT_RESULTS_PATH = PROJECT_ROOT / "results" / "sat" / "encoding_results.csv"
MIP_RESULTS_PATH = PROJECT_ROOT / "results" / "mip" / "mip_results.csv"
CP_RESULTS_PATH = PROJECT_ROOT / "results" / "cp" / "cp_results.csv"
OUTPUT_PATH = PROJECT_ROOT / "results" / "final_comparison.csv"

# 7 cột chung xuất hiện ở cả 3 file CSV
COMMON_COLUMNS = ["instance", "g", "p", "w", "solver", "status", "solve_time"]


def normalize_status(status: str) -> str:
    """Rút gọn thông báo lỗi vượt giới hạn biến/ràng buộc của CPLEX cho gọn bảng."""
    s = status.strip()
    if "problem size limits" in s.lower() or "code=1016" in s.lower():
        return "LICENSE_LIMIT"
    return s


def read_and_extract(filepath: Path, is_sat: bool = False) -> list[dict]:
    """Đọc file CSV và trích xuất các cột chung."""
    if not filepath.exists():
        print(f"[Cảnh báo] Không tìm thấy file: {filepath}")
        return []

    rows = []
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            solver_name = row["solver"].strip()

            # Với file SAT, gắn thêm tên bộ mã hóa (c2_encoding) để phân biệt các biến thể kissat
            if is_sat and row.get("c2_encoding"):
                c2_enc = row["c2_encoding"].strip()
                solver_name = f"{solver_name} ({c2_enc})"

            g_val = int(row["g"])
            p_val = int(row["p"])
            w_val = int(row["w"])

            rows.append(
                {
                    "instance": row["instance"].strip(),
                    "g": g_val,
                    "p": p_val,
                    "w": w_val,
                    "solver": solver_name,
                    "status": normalize_status(row["status"]),
                    "solve_time": float(row["solve_time"]),
                }
            )
    return rows


def main():
    sat_rows = read_and_extract(SAT_RESULTS_PATH, is_sat=True)
    mip_rows = read_and_extract(MIP_RESULTS_PATH, is_sat=False)
    cp_rows = read_and_extract(CP_RESULTS_PATH, is_sat=False)

    all_rows = sat_rows + mip_rows + cp_rows

    if not all_rows:
        print("Không có dữ liệu nào để gộp. Vui lòng kiểm tra lại đường dẫn các file CSV.")
        return

    # Sắp xếp để các bộ dataset (g, p, w) giống nhau xếp liền kề nhau theo thứ tự số học
    all_rows.sort(key=lambda r: (r["g"], r["p"], r["w"], r["solver"]))

    # Tạo thư mục chứa file đầu ra nếu chưa tồn tại
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COMMON_COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"Đã gộp thành công {len(all_rows)} dòng dữ liệu:")
    print(f"  - SAT (encoding_results.csv): {len(sat_rows)} dòng")
    print(f"  - MIP (mip_results.csv):      {len(mip_rows)} dòng")
    print(f"  - CP  (cp_results.csv):       {len(cp_rows)} dòng")
    print(f"Kết quả đã được lưu tại: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()