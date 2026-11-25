"""
Independent Solution Verifier for the Social Golfer Problem (SGP).

Verifies all three formal SGP conditions:
  1. Group Size: |G_{kl}| == p for every group k and week l.
  2. Unique Group Assignment: every player 1..g*p plays in exactly one group each week.
  3. Unique Pairings: no two distinct players share a group more than once across all weeks.
"""

from typing import List, Set, Tuple


def verify_schedule(
    g: int, p: int, w: int, schedule: List[List[List[int]]]
) -> Tuple[bool, str]:
    """
    Verify whether a given schedule is a valid solution for SGP(g, p, w).

    Args:
        g: Number of groups per week.
        p: Number of players per group.
        w: Number of weeks.
        schedule: schedule[week_idx][group_idx] -> list of 1-indexed player IDs.

    Returns:
        (is_valid, message)
    """
    n = g * p
    expected_players = set(range(1, n + 1))

    if len(schedule) != w:
        return False, f"Expected {w} weeks, got {len(schedule)}."

    seen_pairs: Set[Tuple[int, int]] = set()

    for week_idx, week in enumerate(schedule, start=1):
        if len(week) != g:
            return False, f"Week {week_idx}: expected {g} groups, got {len(week)}."

        week_players: List[int] = []
        for group_idx, group in enumerate(week, start=1):
            if len(group) != p:
                return (
                    False,
                    f"Week {week_idx}, Group {group_idx}: expected {p} players, got {len(group)}.",
                )
            if len(set(group)) != p:
                return (
                    False,
                    f"Week {week_idx}, Group {group_idx}: duplicate players in {group}.",
                )

            week_players.extend(group)

            # Check unique pairings
            sorted_group = sorted(group)
            for idx_a in range(p):
                for idx_b in range(idx_a + 1, p):
                    pair = (sorted_group[idx_a], sorted_group[idx_b])
                    if pair in seen_pairs:
                        return (
                            False,
                            f"Duplicate pairing {pair} found in Week {week_idx}, Group {group_idx}.",
                        )
                    seen_pairs.add(pair)

        if len(week_players) != n or set(week_players) != expected_players:
            return (
                False,
                f"Week {week_idx}: players do not partition 1..{n} exactly once.",
            )

    return True, "Valid SGP schedule."
