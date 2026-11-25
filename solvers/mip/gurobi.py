import time
import gurobipy as gp
from gurobipy import GRB


def solve(instance: dict, time_limit: int = 30) -> dict:
    n = instance["num_golfers"]
    p = instance["group_size"]
    w_count = instance["num_weeks"]
    g_count = n // p

    start_time = time.time()
    model = gp.Model("SocialGolfer_Gurobi")
    model.Params.OutputFlag = 0  # Tắt log trên console
    model.Params.TimeLimit = time_limit

    # 1. Biến quyết định: x[i, w, s] = 1 nếu golfer i ở nhóm s tuần w
    x = model.addVars(n, w_count, g_count, vtype=GRB.BINARY, name="x")

    # Biến phụ tuyến tính hóa: y[i, j, w, s] = 1 nếu i và j gặp nhau ở nhóm s tuần w
    y = model.addVars(n, n, w_count, g_count, vtype=GRB.BINARY, name="y")

    # 2. Ràng buộc cơ bản
    # Mỗi golfer thuộc đúng 1 nhóm mỗi tuần
    for i in range(n):
        for w in range(w_count):
            model.addConstr(gp.quicksum(x[i, w, s] for s in range(g_count)) == 1)

    # Mỗi nhóm có đúng p golfer
    for w in range(w_count):
        for s in range(g_count):
            model.addConstr(gp.quicksum(x[i, w, s] for i in range(n)) == p)

    # 3. Ràng buộc không chơi chung quá 1 lần (Tuyến tính hóa tích x[i]*x[j])
    for i in range(n):
        for j in range(i + 1, n):
            for w in range(w_count):
                for s in range(g_count):
                    model.addConstr(y[i, j, w, s] <= x[i, w, s])
                    model.addConstr(y[i, j, w, s] <= x[j, w, s])
                    model.addConstr(y[i, j, w, s] >= x[i, w, s] + x[j, w, s] - 1)

            model.addConstr(
                gp.quicksum(y[i, j, w, s] for w in range(w_count) for s in range(g_count)) <= 1
            )

    # 4. Khóa đối xứng (Symmetry Breaking)
    for i in range(n):
        model.addConstr(x[i, 0, i // p] == 1)
    for w in range(1, w_count):
        model.addConstr(x[0, w, 0] == 1)

    # 5. Giải bài toán (Bài toán thỏa mãn ràng buộc nên hàm mục tiêu = 0)
    model.setObjective(0, GRB.MINIMIZE)
    model.optimize()
    solve_time = time.time() - start_time

    # 6. Chuẩn hóa đầu ra
    schedule = []
    if model.SolCount > 0:
        status = "OPTIMAL" if model.Status == GRB.OPTIMAL else "FEASIBLE"
        for w in range(w_count):
            week_groups = []
            for s in range(g_count):
                members = [i for i in range(n) if x[i, w, s].X > 0.5]
                week_groups.append(members)
            schedule.append(week_groups)
    elif model.Status == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    else:
        status = "UNKNOWN"

    return {
        "solver": "gurobi_mip",
        "status": status,
        "solve_time": round(solve_time, 4),
        "schedule": schedule,
    }