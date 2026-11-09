from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from app.database import fetch_all
from app.auth import get_current_user
from app.heatmap_service import calculate_heatmap_for_users

router = APIRouter(prefix="/api/compare", tags=["Custom Schedule Compare"])

@router.get("")
def compare_schedules(
    user_ids: str = Query(..., description="Comma-separated student IDs, e.g. '1,2,3'"),
    current_user: dict = Depends(get_current_user)
):
    try:
        id_list = [int(uid.strip()) for uid in user_ids.split(",") if uid.strip().isdigit()]
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_ids format.")

    # Ensure current user is in comparison if not already
    if current_user["id"] not in id_list:
        id_list.append(current_user["id"])

    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Select at least one other friend or peer to compare.")

    heatmap = calculate_heatmap_for_users(id_list)
    return heatmap
