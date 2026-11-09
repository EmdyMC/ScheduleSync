from typing import List, Dict, Any, Optional
from app.config import DAYS, TIME_SLOTS, TIME_RANGES, LUNCH_INDEX
from app.database import fetch_all, fetch_one

def calculate_heatmap_for_users(user_ids: List[int], group_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Computes common free time availability across a set of users using relational queries.
    Returns:
        Structured availability matrix, summary statistics, best common slots, and participant lists.
    """
    if not user_ids:
        return {
            "days": DAYS,
            "time_slots": TIME_SLOTS,
            "time_ranges": TIME_RANGES,
            "total_users": 0,
            "users": [],
            "matrix": [],
            "best_slots": []
        }

    # Deduplicate and sort user IDs
    unique_ids = sorted(list(set(user_ids)))
    placeholders = ",".join("?" for _ in unique_ids)

    # 1. Fetch user information
    users_sql = f"""
        SELECT id, username, full_name, reg_no, avatar_color, campus
        FROM users 
        WHERE id IN ({placeholders})
        ORDER BY full_name ASC
    """
    users = fetch_all(users_sql, tuple(unique_ids))
    total_users = len(users)
    user_lookup = {u["id"]: u for u in users}

    # 2. Fetch active busy slots for these users via Relational View or Join
    slots_sql = f"""
        SELECT 
            u.id AS user_id,
            s.day_of_week,
            s.time_index,
            s.is_busy,
            s.slot_code,
            s.course_name
        FROM users u
        JOIN timetables t ON u.id = t.user_id AND t.is_active = 1
        JOIN timetable_slots s ON t.id = s.timetable_id
        WHERE u.id IN ({placeholders}) AND s.is_busy = 1
    """
    busy_records = fetch_all(slots_sql, tuple(unique_ids))

    # Map busy slots: (day, time) -> set of busy user_ids
    busy_map: Dict[tuple, set] = {(d, t): set() for d in range(5) for t in range(11)}
    for r in busy_records:
        d = r["day_of_week"]
        t = r["time_index"]
        if (d, t) in busy_map:
            busy_map[(d, t)].add(r["user_id"])

    # 3. Construct the comprehensive 5x11 result matrix
    grid = []
    best_slots = []

    for d in range(5):
        day_row = []
        for t in range(11):
            is_lunch = (t == LUNCH_INDEX)
            busy_set = busy_map.get((d, t), set())
            
            busy_users = [user_lookup[uid] for uid in busy_set if uid in user_lookup]
            free_users = [u for u in users if u["id"] not in busy_set]
            
            busy_count = len(busy_users)
            free_count = len(free_users)
            free_ratio = (free_count / total_users) if total_users > 0 else 1.0

            # Determine visual classification
            if is_lunch:
                status_class = "lunch"
            elif free_count == total_users:
                status_class = "all-free"
            elif busy_count == total_users:
                status_class = "all-busy"
            elif free_ratio >= 0.6:
                status_class = "mostly-free"
            else:
                status_class = "mostly-busy"

            cell_data = {
                "day_index": d,
                "day_name": DAYS[d],
                "time_index": t,
                "time_label": TIME_SLOTS[t],
                "time_range": TIME_RANGES[t],
                "is_lunch": is_lunch,
                "free_count": free_count,
                "busy_count": busy_count,
                "total_users": total_users,
                "free_percentage": round(free_ratio * 100, 1),
                "status_class": status_class,
                "free_users": free_users,
                "busy_users": busy_users
            }
            day_row.append(cell_data)

            # Record non-lunch slots where 100% of members are free
            if not is_lunch and free_count == total_users and total_users > 0:
                best_slots.append({
                    "day": DAYS[d],
                    "time": TIME_SLOTS[t],
                    "time_range": TIME_RANGES[t],
                    "day_index": d,
                    "time_index": t
                })

        grid.append(day_row)

    # 4. Optional group details if a group was specified
    group_info = None
    if group_id:
        group_info = fetch_one(
            "SELECT id, name, description, invite_code, created_by FROM groups WHERE id = ?",
            (group_id,)
        )

    return {
        "days": DAYS,
        "time_slots": TIME_SLOTS,
        "time_ranges": TIME_RANGES,
        "total_users": total_users,
        "users": users,
        "grid": grid,
        "best_slots": best_slots,
        "group_info": group_info
    }

def calculate_heatmap_for_group(group_id: int) -> Dict[str, Any]:
    """Calculate common free time heatmap for all members of a group."""
    members = fetch_all("SELECT user_id FROM group_members WHERE group_id = ?", (group_id,))
    user_ids = [m["user_id"] for m in members]
    return calculate_heatmap_for_users(user_ids, group_id=group_id)
