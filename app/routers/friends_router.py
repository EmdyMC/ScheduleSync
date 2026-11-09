from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas import FriendRequestAction, FriendResponseAction
from app.database import fetch_one, fetch_all, execute_insert, execute_modify
from app.auth import get_current_user

router = APIRouter(prefix="/api/friends", tags=["Friends System"])

@router.get("")
def list_friends(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    # 1. Accepted Friends using Database View v_user_friends
    friends_sql = """
        SELECT 
            friendship_id,
            friend_id AS id,
            friend_username AS username,
            friend_full_name AS full_name,
            friend_reg_no AS reg_no,
            friend_campus AS campus,
            friend_avatar_color AS avatar_color,
            friendship_date
        FROM v_user_friends
        WHERE user_id = ?
        ORDER BY friend_full_name ASC
    """
    friends = fetch_all(friends_sql, (user_id,))

    # 2. Incoming Requests
    incoming_sql = """
        SELECT 
            f.id AS request_id,
            u.id AS sender_id,
            u.username,
            u.full_name,
            u.reg_no,
            u.avatar_color,
            f.created_at
        FROM friendships f
        JOIN users u ON f.sender_id = u.id
        WHERE f.receiver_id = ? AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """
    incoming = fetch_all(incoming_sql, (user_id,))

    # 3. Outgoing Pending Requests
    outgoing_sql = """
        SELECT 
            f.id AS request_id,
            u.id AS receiver_id,
            u.username,
            u.full_name,
            u.reg_no,
            f.created_at
        FROM friendships f
        JOIN users u ON f.receiver_id = u.id
        WHERE f.sender_id = ? AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """
    outgoing = fetch_all(outgoing_sql, (user_id,))

    return {
        "friends": friends,
        "incoming_requests": incoming,
        "outgoing_requests": outgoing,
        "total_friends": len(friends)
    }

@router.get("/search")
def search_users(q: str = Query(..., min_length=2), current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    query_pattern = f"%{q.strip()}%"

    users_sql = """
        SELECT id, username, full_name, reg_no, campus, avatar_color
        FROM users
        WHERE id != ? AND (username LIKE ? OR full_name LIKE ? OR reg_no LIKE ?)
        LIMIT 20
    """
    candidates = fetch_all(users_sql, (user_id, query_pattern, query_pattern, query_pattern))

    results = []
    for cand in candidates:
        cand_id = cand["id"]
        # Check friendship relationship
        rel = fetch_one(
            """
            SELECT id, sender_id, receiver_id, status 
            FROM friendships 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            """,
            (user_id, cand_id, cand_id, user_id)
        )
        if not rel:
            status_text = "none"
            rel_id = None
        elif rel["status"] == "accepted":
            status_text = "friend"
            rel_id = rel["id"]
        elif rel["sender_id"] == user_id and rel["status"] == "pending":
            status_text = "request_sent"
            rel_id = rel["id"]
        elif rel["receiver_id"] == user_id and rel["status"] == "pending":
            status_text = "request_received"
            rel_id = rel["id"]
        else:
            status_text = rel["status"]
            rel_id = rel["id"]

        results.append({
            **cand,
            "friendship_status": status_text,
            "friendship_id": rel_id
        })

    return {"results": results}

@router.post("/request")
def send_friend_request(payload: FriendRequestAction, current_user: dict = Depends(get_current_user)):
    sender_id = current_user["id"]
    receiver_id = payload.target_user_id

    if sender_id == receiver_id:
        raise HTTPException(status_code=400, detail="Cannot send friend request to yourself.")

    # Check target exists
    target = fetch_one("SELECT id, username FROM users WHERE id = ?", (receiver_id,))
    if not target:
        raise HTTPException(status_code=404, detail="Target user does not exist.")

    # Check existing friendship
    existing = fetch_one(
        "SELECT id, status, sender_id FROM friendships WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)",
        (sender_id, receiver_id, receiver_id, sender_id)
    )
    if existing:
        if existing["status"] == "accepted":
            return {"message": "You are already friends."}
        elif existing["status"] == "pending":
            if existing["sender_id"] == sender_id:
                return {"message": "Friend request already sent."}
            else:
                # If they already sent us a request, automatically accept it!
                execute_modify(
                    "UPDATE friendships SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (existing["id"],)
                )
                return {"message": "Mutual friend request accepted."}
        else:
            # Reopen rejected request
            execute_modify(
                "UPDATE friendships SET sender_id = ?, receiver_id = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (sender_id, receiver_id, existing["id"])
            )
            return {"message": "Friend request resent."}

    # Insert new friendship
    execute_insert(
        "INSERT INTO friendships (sender_id, receiver_id, status) VALUES (?, ?, 'pending')",
        (sender_id, receiver_id)
    )

    return {"message": f"Friend request sent to {target['username']}."}

@router.post("/respond")
def respond_friend_request(payload: FriendResponseAction, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    friendship = fetch_one(
        "SELECT * FROM friendships WHERE id = ? AND receiver_id = ? AND status = 'pending'",
        (payload.friendship_id, user_id)
    )
    if not friendship:
        raise HTTPException(status_code=404, detail="Pending friend request not found.")

    if payload.action == "accepted":
        execute_modify(
            "UPDATE friendships SET status = 'accepted', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.friendship_id,)
        )
        return {"message": "Friend request accepted."}
    else:
        execute_modify(
            "UPDATE friendships SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.friendship_id,)
        )
        return {"message": "Friend request rejected."}

@router.delete("/{friend_id}")
def remove_friend(friend_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    deleted = execute_modify(
        "DELETE FROM friendships WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))",
        (user_id, friend_id, friend_id, user_id)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Friendship record not found.")
    return {"message": "Friend removed successfully."}
