from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

# Xác định thư mục gốc của dự án (Social-Golfer-Problem)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Danh sách các trạng thái được coi là đã giải xong bài toán
SOLVED_STATUSES = {"SAT", "UNSAT", "OPTIMAL", "FEASIBLE", "INFEASIBLE"}


def normalize_status(status: str) -> str:
    """Chuẩn hóa chuỗi trạng thái (rút gọn thông báo lỗi giới hạn của CPLEX)."""
    s = str(status).strip()
    if "problem size limits" in s.lower() or "code=1016" in s.lower():
        return "LICENSE_LIMIT"
    return s.upper()


def plot_cactus(
    csv_path: Path,
    output_filename: str,
    title: str,
    combine_c2_encoding: bool = False,
    log_scale: bool = False,
) -> None:
    """Đọc file CSV, dựng biểu đồ Cactus Plot và lưu cùng thư mục với file CSV."""
    if not csv_path.exists():
        print(f"[Cảnh báo] Không tìm thấy file: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df["clean_status"] = df["status"].apply(normalize_status)

    # Nếu là file SAT (encoding_results.csv), ghép thêm c2_encoding để phân biệt các bộ mã hóa
    if combine_c2_encoding and "c2_encoding" in df.columns:
        df["solver_label"] = (
            df["solver"].astype(str).str.strip()
            + " ("
            + df["c2_encoding"].astype(str).str.strip()
            + ")"
        )
    else:
        df["solver_label"] = df["solver"].astype(str).str.strip()

    # Lọc các dòng đã giải thành công
    solved_df = df[df["clean_status"].isin(SOLVED_STATUSES)].copy()

    plt.figure(figsize=(10, 6), dpi=300)
    markers = ["o", "s", "^", "D", "v", "P", "X", "*", "<", ">"]

    solvers = sorted(df["solver_label"].unique())
    has_data = False

    for idx, solver in enumerate(solvers):
        times = (
            solved_df[solved_df["solver_label"] == solver]["solve_time"]
            .astype(float)
            .sort_values()
            .tolist()
        )
        if not times:
            # Nếu solver không giải được bộ nào (0 instance), vẽ điểm tại gốc hoặc ghi chú trong legend
            plt.plot(
                [],
                [],
                marker=markers[idx % len(markers)],
                label=f"{solver} (0 solved)",
            )
            continue

        has_data = True
        x_vals = list(range(1, len(times) + 1))

        # Với log-scale, thay thời gian 0.0s bằng 1e-4s để không bị ẩn trên trục log
        y_vals = [max(t, 1e-4) if log_scale else t for t in times]

        plt.plot(
            x_vals,
            y_vals,
            marker=markers[idx % len(markers)],
            markersize=5,
            linewidth=1.8,
            alpha=0.9,
            label=f"{solver} ({len(times)} solved)",
        )

    plt.title(title, fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Số lượng bộ dữ liệu đã giải được (Instances Solved)", fontsize=11)
    plt.ylabel(
        "Thời gian giải (giây) - Thang log" if log_scale else "Thời gian giải (giây)",
        fontsize=11,
    )

    if log_scale and has_data:
        plt.yscale("log")

    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="Bộ giải (Solvers)", loc="upper left", frameon=True, fontsize=9)
    plt.tight_layout()

    output_path = csv_path.parent / output_filename
    plt.savefig(output_path)
    plt.close()
    print(f"Đã lưu biểu đồ: {output_path}")


def main():
    # 1. CP Cactus Plot -> lưu tại results/cp/cp_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "cp" / "cp_results.csv",
        output_filename="cp_cactus_plot.png",
        title="Cactus Plot - So sánh các bộ giải Constraint Programming (CP)",
        combine_c2_encoding=False,
        log_scale=False,
    )

    # 2. MIP Cactus Plot -> lưu tại results/mip/mip_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "mip" / "mip_results.csv",
        output_filename="mip_cactus_plot.png",
        title="Cactus Plot - So sánh các bộ giải Mixed-Integer Programming (MIP)",
        combine_c2_encoding=False,
        log_scale=False,
    )

    # 3. SAT Cactus Plot -> lưu tại results/sat/sat_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "sat" / "encoding_results.csv",
        output_filename="sat_cactus_plot.png",
        title="Cactus Plot - So sánh các kỹ thuật mã hóa SAT (Kissat)",
        combine_c2_encoding=True,
        log_scale=False,
    )

    # 4. Final Cactus Plot -> lưu tại results/final_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "final_comparison.csv",
        output_filename="final_cactus_plot.png",
        title="Cactus Plot - So sánh tổng hợp các bộ giải SAT, CP và MIP",
        combine_c2_encoding=False,
        log_scale=True,  # Dùng thang log để quan sát rõ cả nhóm giải nhanh (<0.5s) và nhóm chạy tới 30s
    )


if __name__ == "__main__":
    main()