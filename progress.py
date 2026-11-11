"""Game rules, kept free of database and Flask code so they are easy to test."""
from collections import defaultdict

XP_PER_STEP = 10  # same for every step: rewards showing up, never intensity


def summarize(steps, completion_rows, today_iso):
    """Work out today's progress and how many full days the user has finished."""
    all_ids = {s["id"] for s in steps}
    by_day = defaultdict(set)
    for row in completion_rows:
        by_day[row["completed_on"]].add(row["step_id"])
    done_today = by_day.get(today_iso, set()) & all_ids
    full_days = sum(1 for ids in by_day.values() if all_ids and all_ids <= ids)
    return {
        "done_today": done_today,
        "day_complete": bool(all_ids) and all_ids <= done_today,
        "full_days": full_days,
        "phase_completions": len(completion_rows),
    }


def flag_steps(steps, done_today):
    """Add done/unlocked flags. A step unlocks once the one before it is done."""
    flagged = []
    previous_done = True
    for step in steps:
        done = step["id"] in done_today
        flagged.append({**step, "done": done, "unlocked": previous_done})
        previous_done = done
    return flagged
