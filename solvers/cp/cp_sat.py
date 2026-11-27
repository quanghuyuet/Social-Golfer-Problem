import time
from ortools.sat.python import cp_model


def solve(instance: dict, time_limit: int = 30) -> dict:
    num_golfers = instance["num_golfers"]
    group_size = instance["group_size"]
    num_weeks = instance["num_weeks"]
    num_groups = num_golfers // group_size

    start_time = time.time()
    model = cp_model.CpModel()

    # 1. TẠO BIẾN QUYẾT ĐỊNH
    x = {}
    for i in range(num_golfers):
        for w in range(num_weeks):
            for s in range(num_groups):
                x[i, w, s] = model.NewBoolVar(f"x_{i}_{w}_{s}")

    # 2. RÀNG BUỘC CƠ BẢN
    for i in range(num_golfers):
        for w in range(num_weeks):
            model.AddExactlyOne(x[i, w, s] for s in range(num_groups))

    for w in range(num_weeks):
        for s in range(num_groups):
            model.Add(sum(x[i, w, s] for i in range(num_golfers)) == group_size)

    # 3. RÀNG BUỘC KHÔNG CHƠI CHUNG QUÁ 1 LẦN
    for i in range(num_golfers):
        for j in range(i + 1, num_golfers):
            pair_meets = []
            for w in range(num_weeks):
                for s in range(num_groups):
                    meet = model.NewBoolVar(f"meet_{i}_{j}_{w}_{s}")
                    model.AddBoolAnd([x[i, w, s], x[j, w, s]]).OnlyEnforceIf(meet)
                    model.AddBoolOr([x[i, w, s].Not(), x[j, w, s].Not()]).OnlyEnforceIf(meet.Not())
                    pair_meets.append(meet)

            model.Add(sum(pair_meets) <= 1)

    # 4. TRÁNH ĐỐI XỨNG (SYMMETRY BREAKING)
    for i in range(num_golfers):
        target_group = i // group_size
        model.Add(x[i, 0, target_group] == 1)

    for w in range(1, num_weeks):
        model.Add(x[0, w, 0] == 1)

    # 5. CẤU HÌNH SOLVER VÀ GIẢI
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = 8

    status_code = solver.Solve(model)
    solve_time = time.time() - start_time

    # 6. CHUẨN HÓA ĐẦU RA
    schedule = []
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        status = "OPTIMAL" if status_code == cp_model.OPTIMAL else "FEASIBLE"
        for w in range(num_weeks):
            week_groups = []
            for s in range(num_groups):
                group_members = [
                    i for i in range(num_golfers) if solver.Value(x[i, w, s]) == 1
                ]
                week_groups.append(group_members)
            schedule.append(week_groups)
    elif status_code == cp_model.INFEASIBLE:
        status = "INFEASIBLE"
    else:
        status = "UNKNOWN"

    return {
        "solver": "cp_sat",
        "status": status,
        "solve_time": round(solve_time, 4),
        "schedule": schedule,
    }