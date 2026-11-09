import secrets
import string
from fastapi import APIRouter, HTTPException, Depends
from app.schemas import CreateGroupRequest, JoinGroupRequest
from app.database import fetch_one, fetch_all, execute_insert, execute_modify, get_db_context
from app.auth import get_current_user
from app.heatmap_service import calculate_heatmap_for_group

router = APIRouter(prefix="/api/groups", tags=["Groups & Teams"])

def generate_invite_code(length: int = 6) -> str:
    """Generate a clean, uppercase alphanumeric invite code."""
    chars = string.ascii_uppercase + string.digits
    # Exclude ambiguous characters
    chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return "".join(secrets.choice(chars) for _ in range(length))

@router.get("")
def list_my_groups(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    groups_sql = """
        SELECT 
            g.id,
            g.name,
            g.description,
            g.invite_code,
            g.created_by,
            creator.full_name AS creator_name,
            gm.role AS my_role,
            gm.joined_at,
            (SELECT COUNT(*) FROM group_members WHERE group_id = g.id) AS member_count
        FROM group_members gm
        JOIN groups g ON gm.group_id = g.id
        JOIN users creator ON g.created_by = creator.id
        WHERE gm.user_id = ?
        ORDER BY g.created_at DESC
    """
    groups = fetch_all(groups_sql, (user_id,))
    return {"groups": groups, "total_groups": len(groups)}

@router.post("/create")
def create_group(payload: CreateGroupRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Generate unique invite code
    invite_code = generate_invite_code()
    while fetch_one("SELECT id FROM groups WHERE invite_code = ?", (invite_code,)):
        invite_code = generate_invite_code()

    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO groups (name, description, created_by, invite_code) VALUES (?, ?, ?, ?)",
            (payload.name.strip(), payload.description.strip() if payload.description else None, user_id, invite_code)
        )
        group_id = cursor.lastrowid

        # Add creator as admin member
        cursor.execute(
            "INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, 'admin')",
            (group_id, user_id)
        )

    return {
        "message": f"Group '{payload.name}' created successfully.",
        "group": {
            "id": group_id,
            "name": payload.name,
            "description": payload.description,
            "invite_code": invite_code,
            "role": "admin"
        }
    }

@router.post("/join")
def join_group(payload: JoinGroupRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    code = payload.invite_code.strip().upper()

    group = fetch_one("SELECT * FROM groups WHERE invite_code = ?", (code,))
    if not group:
        raise HTTPException(status_code=404, detail="Invalid invite code. No group found.")

    # Check if already a member
    member = fetch_one("SELECT id FROM group_members WHERE group_id = ? AND user_id = ?", (group["id"], user_id))
    if member:
        return {"message": "You are already a member of this group.", "group_id": group["id"]}

    execute_insert(
        "INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, 'member')",
        (group["id"], user_id)
    )

    return {
        "message": f"Successfully joined '{group['name']}'.",
        "group_id": group["id"],
        "group_name": group["name"]
    }

@router.get("/{group_id}")
def get_group_details(group_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    # Verify user is a member of the group
    is_member = fetch_one("SELECT role FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this group.")

    group = fetch_one(
        """
        SELECT g.*, creator.full_name AS creator_name
        FROM groups g
        JOIN users creator ON g.created_by = creator.id
        WHERE g.id = ?
        """,
        (group_id,)
    )
    if not group:
        raise HTTPException(status_code=404, detail="Group not found.")

    # Fetch members from View
    members = fetch_all(
        """
        SELECT user_id, username, full_name, reg_no, avatar_color, role, joined_at
        FROM v_group_members_details
        WHERE group_id = ?
        ORDER BY role DESC, full_name ASC
        """,
        (group_id,)
    )

    return {
        "group": dict(group),
        "my_role": is_member["role"],
        "members": members,
        "total_members": len(members)
    }

@router.get("/{group_id}/heatmap")
def get_group_heatmap(group_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    is_member = fetch_one("SELECT role FROM group_members WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not a member of this group.")

    heatmap = calculate_heatmap_for_group(group_id)
    return heatmap

@router.delete("/{group_id}/leave")
def leave_group(group_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    deleted = execute_modify(
        "DELETE FROM group_members WHERE group_id = ? AND user_id = ?",
        (group_id, user_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Membership record not found.")

    # If no members left in group, delete the group
    remaining = fetch_one("SELECT COUNT(*) AS c FROM group_members WHERE group_id = ?", (group_id,))
    if remaining and remaining["c"] == 0:
        execute_modify("DELETE FROM groups WHERE id = ?", (group_id,))

    return {"message": "Left group successfully."}
