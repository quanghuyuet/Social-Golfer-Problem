import time
from docplex.cp.model import CpoModel


def solve(instance: dict, time_limit: int = 60) -> dict:
    n = instance["num_golfers"]
    p = instance["group_size"]
    w_count = instance["num_weeks"]
    g_count = n // p

    start_time = time.time()
    mdl = CpoModel(name="SocialGolfer_CPLEX_CP")

    # 1. Biến quyết định: group[i][w] là chỉ số nhóm (0 .. g_count-1) của golfer i tại tuần w
    group = [
        [mdl.integer_var(0, g_count - 1, name=f"g_{i}_{w}") for w in range(w_count)]
        for i in range(n)
    ]

    # 2. Ràng buộc kích thước nhóm: Mỗi tuần, mỗi nhóm xuất hiện đúng p lần
    for w in range(w_count):
        week_vars = [group[i][w] for i in range(n)]
        for s in range(g_count):
            mdl.add(mdl.count(week_vars, s) == p)

    # 3. Ràng buộc không gặp lại quá 1 lần:
    # Tổng số tuần mà group[i][w] == group[j][w] <= 1
    for i in range(n):
        for j in range(i + 1, n):
            mdl.add(mdl.sum(group[i][w] == group[j][w] for w in range(w_count)) <= 1)

    # 4. Khóa đối xứng
    for i in range(n):
        mdl.add(group[i][0] == i // p)
    for w in range(1, w_count):
        mdl.add(group[0][w] == 0)

    # 5. Giải bài toán
    msol = mdl.solve(TimeLimit=time_limit, LogVerbosity="Quiet")
    solve_time = time.time() - start_time

    # 6. Chuẩn hóa đầu ra
    schedule = []
    if msol:
        status = "OPTIMAL" if msol.get_solve_status() == "Optimal" else "FEASIBLE"
        for w in range(w_count):
            week_groups = [[] for _ in range(g_count)]
            for i in range(n):
                assigned_group = msol[group[i][w]]
                week_groups[assigned_group].append(i)
            schedule.append(week_groups)
    elif msol.get_solve_status() == "Infeasible":
        status = "INFEASIBLE"
    else:
        status = "UNKNOWN"

    return {
        "solver": "cplex_cp",
        "status": status,
        "solve_time": round(solve_time, 4),
        "schedule": schedule,
    }