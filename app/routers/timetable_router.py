import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from app.schemas import TimetableUpdate
from app.database import fetch_one, fetch_all, execute_insert, execute_modify, get_db_context
from app.auth import get_current_user
from app.config import UPLOAD_DIR, DAYS, TIME_SLOTS, TIME_RANGES, LUNCH_INDEX, SLOT_TEMPLATE
from app.ocr_service import extract_slots_from_image, is_ocr_available

router = APIRouter(prefix="/api/timetable", tags=["Timetable Management"])

@router.get("/my-slots")
def get_my_slots(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # 1. Fetch active timetable (or create if missing)
    tt = fetch_one("SELECT * FROM timetables WHERE user_id = ? AND is_active = 1", (user_id,))
    if not tt:
        tt_id = execute_insert(
            "INSERT INTO timetables (user_id, semester, title, is_active) VALUES (?, 'Winter Semester 2026', 'My Academic Schedule', 1)",
            (user_id,)
        )
        # Populate default empty slots
        with get_db_context() as conn:
            cursor = conn.cursor()
            default_slots = [
                (tt_id, d, t, 0, None, None)
                for d in range(5) for t in range(11)
            ]
            cursor.executemany(
                "INSERT INTO timetable_slots (timetable_id, day_of_week, time_index, is_busy, slot_code, course_name) VALUES (?, ?, ?, ?, ?, ?)",
                default_slots
            )
        tt = fetch_one("SELECT * FROM timetables WHERE id = ?", (tt_id,))

    # 2. Fetch all slots
    slots = fetch_all(
        "SELECT id, day_of_week, time_index, is_busy, slot_code, course_name FROM timetable_slots WHERE timetable_id = ? ORDER BY day_of_week, time_index",
        (tt["id"],)
    )

    # Reconstruct 5x11 matrix
    grid = [[0 for _ in range(11)] for _ in range(5)]
    slot_details = [[{} for _ in range(11)] for _ in range(5)]
    
    for s in slots:
        d = s["day_of_week"]
        t = s["time_index"]
        if 0 <= d < 5 and 0 <= t < 11:
            grid[d][t] = s["is_busy"]
            slot_details[d][t] = {
                "id": s["id"],
                "day": d,
                "time": t,
                "is_busy": s["is_busy"],
                "slot_code": s["slot_code"] or (SLOT_TEMPLATE[d][t][0] if t != LUNCH_INDEX else "LUNCH"),
                "course_name": s["course_name"] or ""
            }

    return {
        "timetable": dict(tt),
        "days": DAYS,
        "time_slots": TIME_SLOTS,
        "time_ranges": TIME_RANGES,
        "matrix": grid,
        "slot_details": slot_details,
        "ocr_available": is_ocr_available()
    }

@router.post("/update-slots")
def update_slots(payload: TimetableUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    tt = fetch_one("SELECT id FROM timetables WHERE user_id = ? AND is_active = 1", (user_id,))
    if not tt:
        raise HTTPException(status_code=404, detail="Active timetable not found.")

    timetable_id = tt["id"]

    with get_db_context() as conn:
        cursor = conn.cursor()
        
        # Update metadata if provided
        cursor.execute(
            "UPDATE timetables SET semester = ?, title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (payload.semester, payload.title, timetable_id)
        )

        # Batch upsert slots
        for slot in payload.slots:
            cursor.execute(
                """
                INSERT INTO timetable_slots (timetable_id, day_of_week, time_index, is_busy, slot_code, course_name)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(timetable_id, day_of_week, time_index) DO UPDATE SET
                    is_busy = excluded.is_busy,
                    slot_code = excluded.slot_code,
                    course_name = excluded.course_name
                """,
                (
                    timetable_id,
                    slot.day_of_week,
                    slot.time_index,
                    slot.is_busy,
                    slot.slot_code,
                    slot.course_name
                )
            )

    return {"message": "Timetable slots saved successfully."}

@router.post("/upload-ocr")
async def upload_ocr(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Validate extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".png", ".jpg", ".jpeg", ".webp"]:
        raise HTTPException(status_code=400, detail="Only image files (.png, .jpg, .jpeg) are supported.")

    # Save to disk
    unique_filename = f"tt_{user_id}_{uuid.uuid4().hex[:8]}{file_ext}"
    saved_path = UPLOAD_DIR / unique_filename

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run OCR Extraction
    ocr_result = extract_slots_from_image(str(saved_path))
    
    # Fetch active timetable
    tt = fetch_one("SELECT id FROM timetables WHERE user_id = ? AND is_active = 1", (user_id,))
    if not tt:
        raise HTTPException(status_code=404, detail="Active timetable not found.")

    timetable_id = tt["id"]

    # If OCR extracted slots, update the DB
    if ocr_result["success"]:
        matrix = ocr_result["matrix"]
        with get_db_context() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE timetables SET original_image_path = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (str(saved_path.name), timetable_id)
            )
            for d in range(5):
                for t in range(11):
                    is_busy = matrix[d][t]
                    slot_code = SLOT_TEMPLATE[d][t][0] if t != LUNCH_INDEX else "LUNCH"
                    cursor.execute(
                        """
                        INSERT INTO timetable_slots (timetable_id, day_of_week, time_index, is_busy, slot_code)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(timetable_id, day_of_week, time_index) DO UPDATE SET
                            is_busy = excluded.is_busy,
                            slot_code = excluded.slot_code
                        """,
                        (timetable_id, d, t, is_busy, slot_code)
                    )

    return {
        "message": "OCR timetable extraction processed.",
        "ocr_result": ocr_result,
        "image_url": f"/uploads/{unique_filename}"
    }

@router.post("/clear-slots")
def clear_slots(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    tt = fetch_one("SELECT id FROM timetables WHERE user_id = ? AND is_active = 1", (user_id,))
    if tt:
        execute_modify(
            "UPDATE timetable_slots SET is_busy = 0 WHERE timetable_id = ?",
            (tt["id"],)
        )
    return {"message": "All timetable slots reset to Free."}
