import secrets
import datetime
from fastapi import APIRouter, HTTPException, Depends
from app.schemas import CreateShareLinkRequest
from app.database import fetch_one, execute_insert
from app.auth import get_current_user
from app.heatmap_service import calculate_heatmap_for_group, calculate_heatmap_for_users

router = APIRouter(prefix="/api/share", tags=["Sharing & Public Links"])

@router.post("/create")
def create_share_link(payload: CreateShareLinkRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    token = secrets.token_urlsafe(16)
    
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=payload.expires_in_days)
        expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    else:
        expires_at_str = None

    execute_insert(
        """
        INSERT INTO share_links (token, title, user_id, group_id, created_by, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (token, payload.title, payload.user_id, payload.group_id, user_id, expires_at_str)
    )

    return {
        "token": token,
        "share_url": f"/share/{token}",
        "title": payload.title,
        "expires_at": expires_at_str
    }

@router.get("/{token}")
def get_shared_heatmap(token: str):
    link = fetch_one("SELECT * FROM share_links WHERE token = ?", (token,))
    if not link:
        raise HTTPException(status_code=404, detail="Shared schedule link not found.")

    # Check expiration if set
    if link["expires_at"]:
        try:
            exp = datetime.datetime.fromisoformat(link["expires_at"])
            if datetime.datetime.now(datetime.timezone.utc) > exp:
                raise HTTPException(status_code=410, detail="This shared schedule link has expired.")
        except Exception:
            pass

    if link["group_id"]:
        heatmap = calculate_heatmap_for_group(link["group_id"])
    elif link["user_id"]:
        heatmap = calculate_heatmap_for_users([link["user_id"]])
    else:
        raise HTTPException(status_code=400, detail="Invalid share link target.")

    return {
        "title": link["title"],
        "token": token,
        "created_at": link["created_at"],
        "heatmap": heatmap
    }
