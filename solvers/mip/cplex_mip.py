import time
from docplex.mp.model import Model


def solve(instance: dict, time_limit: int = 30) -> dict:
    n = instance["num_golfers"]
    p = instance["group_size"]
    w_count = instance["num_weeks"]
    g_count = n // p

    start_time = time.time()
    mdl = Model(name="SocialGolfer_CPLEX_MIP")
    mdl.set_time_limit(time_limit)

    # 1. Biến quyết định
    x = mdl.binary_var_cube(n, w_count, g_count, name="x")
    y = {}
    for i in range(n):
        for j in range(i + 1, n):
            for w in range(w_count):
                for s in range(g_count):
                    y[i, j, w, s] = mdl.binary_var(name=f"y_{i}_{j}_{w}_{s}")

    # 2. Ràng buộc cơ bản
    for i in range(n):
        for w in range(w_count):
            mdl.add_constraint(mdl.sum(x[i, w, s] for s in range(g_count)) == 1)

    for w in range(w_count):
        for s in range(g_count):
            mdl.add_constraint(mdl.sum(x[i, w, s] for i in range(n)) == p)

    # 3. Ràng buộc không gặp lại quá 1 lần
    for i in range(n):
        for j in range(i + 1, n):
            for w in range(w_count):
                for s in range(g_count):
                    mdl.add_constraint(y[i, j, w, s] <= x[i, w, s])
                    mdl.add_constraint(y[i, j, w, s] <= x[j, w, s])
                    mdl.add_constraint(y[i, j, w, s] >= x[i, w, s] + x[j, w, s] - 1)

            mdl.add_constraint(
                mdl.sum(y[i, j, w, s] for w in range(w_count) for s in range(g_count)) <= 1
            )

    # 4. Khóa đối xứng
    for i in range(n):
        mdl.add_constraint(x[i, 0, i // p] == 1)
    for w in range(1, w_count):
        mdl.add_constraint(x[0, w, 0] == 1)

    # 5. Giải bài toán
    solution = mdl.solve(log_output=False)
    solve_time = time.time() - start_time

    # 6. Chuẩn hóa đầu ra
    schedule = []
    if solution:
        solve_status = mdl.solve_details.status
        status = "OPTIMAL" if "optimal" in solve_status.lower() else "FEASIBLE"
        for w in range(w_count):
            week_groups = []
            for s in range(g_count):
                members = [i for i in range(n) if solution.get_value(x[i, w, s]) > 0.5]
                week_groups.append(members)
            schedule.append(week_groups)
    else:
        solve_status = mdl.solve_details.status
        status = "INFEASIBLE" if "infeasible" in solve_status.lower() else "UNKNOWN"

    return {
        "solver": "cplex_mip",
        "status": status,
        "solve_time": round(solve_time, 4),
        "schedule": schedule,
    }