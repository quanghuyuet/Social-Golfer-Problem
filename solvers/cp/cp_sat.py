from ortools.sat.python import cp_model


def solve_social_golfer(num_golfers, group_size, num_weeks, time_limit_seconds=30):
    num_groups = num_golfers // group_size
    model = cp_model.CpModel()

    # ----------------------------------------------------
    # 1. TẠO BIẾN QUYẾT ĐỊNH
    # ----------------------------------------------------
    # x[i, w, s] = 1 nếu Golfer i ở Nhóm s tuần w
    x = {}
    for i in range(num_golfers):
        for w in range(num_weeks):
            for s in range(num_groups):
                x[i, w, s] = model.NewBoolVar(f"x_{i}_{w}_{s}")

    # ----------------------------------------------------
    # 2. RÀNG BUỘC CƠ BẢN
    # ----------------------------------------------------
    # C1: Mỗi golfer thuộc đúng 1 nhóm mỗi tuần
    for i in range(num_golfers):
        for w in range(num_weeks):
            model.AddExactlyOne(x[i, w, s] for s in range(num_groups))

    # C2: Mỗi nhóm có đúng group_size (p) golfer
    for w in range(num_weeks):
        for s in range(num_groups):
            model.Add(
                sum(x[i, w, s] for i in range(num_golfers)) == group_size
            )

    # ----------------------------------------------------
    # 3. RÀNG BUỘC KHÔNG CHƠI CHUNG QUÁ 1 LẦN
    # ----------------------------------------------------
    for i in range(num_golfers):
        for j in range(i + 1, num_golfers):
            pair_meets = []
            for w in range(num_weeks):
                for s in range(num_groups):
                    # meet = x[i,w,s] AND x[j,w,s]
                    meet = model.NewBoolVar(f"meet_{i}_{j}_{w}_{s}")
                    model.AddBoolAnd([x[i, w, s], x[j, w, s]]).OnlyEnforceIf(
                        meet
                    )
                    model.AddBoolOr(
                        [x[i, w, s].Not(), x[j, w, s].Not()]
                    ).OnlyEnforceIf(meet.Not())
                    pair_meets.append(meet)

            # Tổng số tuần gặp nhau của cặp (i, j) <= 1
            model.Add(sum(pair_meets) <= 1)

    # ----------------------------------------------------
    # 4. TRÁNH ĐỐI XỨNG (SYMMETRY BREAKING)
    # ----------------------------------------------------
    # Tuần 0: Cố định vị trí golfer (0..p-1 vào nhóm 0, p..2p-1 vào nhóm 1,...)
    for i in range(num_golfers):
        target_group = i // group_size
        model.Add(x[i, 0, target_group] == 1)

    # Golfer 0 luôn nằm ở Nhóm 0 trong mọi tuần
    for w in range(1, num_weeks):
        model.Add(x[0, w, 0] == 1)

    # ----------------------------------------------------
    # 5. CẤU HÌNH SOLVER VÀ GIẢI
    # ----------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_seconds
    solver.parameters.num_search_workers = 8  # Tận dụng đa nhân CPU

    status = solver.Solve(model)

    # ----------------------------------------------------
    # 6. IN KẾT QUẢ
    # ----------------------------------------------------
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print(f"--- TÌM THẤY LỜI GIẢI CHO {num_weeks} TUẦN ---")
        for w in range(num_weeks):
            print(f"\nTuần {w + 1}:")
            for s in range(num_groups):
                group_members = [
                    i
                    for i in range(num_golfers)
                    if solver.Value(x[i, w, s]) == 1
                ]
                print(f"  Nhóm {s + 1}: {group_members}")
    else:
        print("Không tìm thấy lời giải hợp lệ trong thời gian cho phép.")


# Chạy thử nghiệm với 32 golfer, nhóm 4 người (8 nhóm), chơi trong 7 tuần
solve_social_golfer(num_golfers=32, group_size=4, num_weeks=7)