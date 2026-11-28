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
    encoding_col: str | None = None,
    log_scale: bool = False,
) -> None:
    """Đọc file CSV, dựng biểu đồ Cactus Plot và lưu cùng thư mục với file CSV."""
    if not csv_path.exists():
        print(f"[Cảnh báo] Không tìm thấy file: {csv_path}")
        return

    df = pd.read_csv(csv_path)
    df["clean_status"] = df["status"].apply(normalize_status)

    # Nếu chỉ định cột kỹ thuật mã hóa (ví dụ 'c2_encoding' hoặc 'c1_encoding'), ghép vào tên solver
    if encoding_col and encoding_col in df.columns:
        df["solver_label"] = (
            df["solver"].astype(str).str.strip()
            + " ("
            + df[encoding_col].astype(str).str.strip()
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
            .dropna()
            .astype(float)
            .sort_values()
            .tolist()
        )
        if not times:
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
        encoding_col=None,
        log_scale=False,
    )

    # 2. MIP Cactus Plot -> lưu tại results/mip/mip_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "mip" / "mip_results.csv",
        output_filename="mip_cactus_plot.png",
        title="Cactus Plot - So sánh các bộ giải Mixed-Integer Programming (MIP)",
        encoding_col=None,
        log_scale=False,
    )

    # 3. SAT Cactus Plot (C2 Exactly-K) -> lưu tại results/sat/sat_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "sat" / "encoding_results.csv",
        output_filename="sat_cactus_plot.png",
        title="Cactus Plot - So sánh các kỹ thuật mã hóa C2 Exactly-K (Kissat)",
        encoding_col="c2_encoding",
        log_scale=False,
    )

    # 4. SAT Cactus Plot (C1 AMO) -> lưu tại results/sat/cactus_plot_c1_amo.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "sat" / "c1_amo_results.csv",
        output_filename="cactus_plot_c1_amo.png",
        title="Cactus Plot - So sánh các kỹ thuật mã hóa C1 At-Most-One (Kissat)",
        encoding_col="c1_encoding",
        log_scale=False,
    )

    # 5. Final Cactus Plot -> lưu tại results/final_cactus_plot.png
    plot_cactus(
        csv_path=PROJECT_ROOT / "results" / "final_comparison.csv",
        output_filename="final_cactus_plot.png",
        title="Cactus Plot - So sánh tổng hợp các bộ giải SAT, CP và MIP",
        encoding_col=None,
        log_scale=True,
    )


if __name__ == "__main__":
    main()