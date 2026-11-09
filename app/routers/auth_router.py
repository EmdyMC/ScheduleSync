from fastapi import APIRouter, HTTPException, status, Depends, Response
from app.schemas import UserRegister, UserLogin, UserProfileUpdate
from app.database import fetch_one, execute_insert, execute_modify, get_db_context
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register")
def register(payload: UserRegister, response: Response):
    # Check if username or email already exists
    existing = fetch_one(
        "SELECT id, username, email FROM users WHERE username = ? OR email = ?",
        (payload.username.strip(), payload.email.strip().lower())
    )
    if existing:
        if existing["username"].lower() == payload.username.strip().lower():
            raise HTTPException(status_code=400, detail="Username is already taken.")
        else:
            raise HTTPException(status_code=400, detail="Email is already registered.")

    hashed_pw = hash_password(payload.password)
    
    with get_db_context() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, full_name, reg_no, campus, avatar_color)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.username.strip(),
                payload.email.strip().lower(),
                hashed_pw,
                payload.full_name.strip(),
                payload.reg_no.strip() if payload.reg_no else None,
                payload.campus or "VIT Chennai",
                payload.avatar_color or "#4f46e5"
            )
        )
        user_id = cursor.lastrowid

        # Automatically create an active default timetable for the user
        cursor.execute(
            """
            INSERT INTO timetables (user_id, semester, title, is_active)
            VALUES (?, 'Winter Semester 2026', 'My Academic Schedule', 1)
            """,
            (user_id,)
        )
        timetable_id = cursor.lastrowid

        # Initialize all 55 slots (5 days x 11 slots) as 0 (Free)
        slots_data = [
            (timetable_id, day, time_idx, 0, None, None)
            for day in range(5)
            for time_idx in range(11)
        ]
        cursor.executemany(
            """
            INSERT INTO timetable_slots (timetable_id, day_of_week, time_index, is_busy, slot_code, course_name)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            slots_data
        )

    # Generate token
    token = create_access_token({"sub": str(user_id), "username": payload.username})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, samesite="lax")

    return {
        "message": "User registered successfully.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "username": payload.username,
            "email": payload.email,
            "full_name": payload.full_name,
            "reg_no": payload.reg_no,
            "campus": payload.campus
        }
    }

@router.post("/login")
def login(payload: UserLogin, response: Response):
    identifier = payload.username_or_email.strip()
    user = fetch_one(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (identifier, identifier.lower())
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password."
        )

    token = create_access_token({"sub": str(user["id"]), "username": user["username"]})
    response.set_cookie(key="access_token", value=f"Bearer {token}", httponly=True, samesite="lax")

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "reg_no": user["reg_no"],
            "campus": user["campus"],
            "avatar_color": user["avatar_color"]
        }
    }

@router.get("/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

@router.put("/profile")
def update_profile(payload: UserProfileUpdate, current_user: dict = Depends(get_current_user)):
    updates = []
    params = []
    if payload.full_name is not None:
        updates.append("full_name = ?")
        params.append(payload.full_name.strip())
    if payload.reg_no is not None:
        updates.append("reg_no = ?")
        params.append(payload.reg_no.strip())
    if payload.campus is not None:
        updates.append("campus = ?")
        params.append(payload.campus.strip())
    if payload.avatar_color is not None:
        updates.append("avatar_color = ?")
        params.append(payload.avatar_color.strip())

    if updates:
        params.append(current_user["id"])
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        execute_modify(sql, tuple(params))

    updated_user = fetch_one(
        "SELECT id, username, email, full_name, reg_no, campus, avatar_color, created_at FROM users WHERE id = ?",
        (current_user["id"],)
    )
    return {"message": "Profile updated successfully.", "user": updated_user}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "Logged out successfully."}
