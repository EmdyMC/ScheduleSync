import os
import re
import cv2
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Set
from app.config import TESSERACT_CMD, LUNCH_INDEX

# 1. THE EXACT HARDCODED SLOT TEMPLATE FROM main.py
SLOT_TEMPLATE = [
    # MONDAY
    [
        ["A1", "AI", "AL", "L1", "LI", "LL"], 
        ["F1", "FI", "FL", "L2"], 
        ["D1", "DI", "DL", "L3"], 
        ["TB1", "TBI", "TBL", "L4"], 
        ["TG1", "TGI", "TGL", "L5"], 
        ["L6", "S11", "S1I", "S1L", "SI1", "SII", "SIL", "SL1", "SLI", "SLL"], 
        ["LUNCH"], 
        ["A2", "L31", "L3I", "L3L"], 
        ["F2", "L32"], 
        ["D2", "L33"], 
        ["TB2", "L34"]
    ],
    # TUESDAY
    [
        ["B1", "BI", "BL", "L7"], 
        ["G1", "GI", "GL", "L8"], 
        ["E1", "EI", "EL", "L9"], 
        ["TC1", "TCI", "TCL", "L10", "LI0", "LL0"], 
        ["TAA1", "TAAI", "TAAL", "L11", "L1I", "L1L", "LI1", "LII", "LIL", "LL1", "LLI", "LLL"], 
        ["L12", "LI2", "LL2"], 
        ["LUNCH"], 
        ["B2", "L37"], 
        ["G2", "L38"], 
        ["E2", "L39"], 
        ["TC2", "L40"]
    ],
    # WEDNESDAY
    [
        ["C1", "CI", "CL", "L13", "LI3", "LL3"], 
        ["A1", "AI", "AL", "L14", "LI4", "LL4"], 
        ["F1", "FI", "FL", "L15", "LI5", "LL5"], 
        ["TD1", "TDI", "TDL", "L16", "LI6", "LL6"], 
        ["TBB1", "TBBI", "TBBL", "L17", "LI7", "LL7"], 
        ["L18", "LI8", "LL8"], 
        ["LUNCH"], 
        ["C2", "L43"], 
        ["A2", "L44"], 
        ["F2", "L45"], 
        ["TD2", "L46"]
    ],
    # THURSDAY
    [
        ["D1", "DI", "DL", "L19", "LI9", "LL9"], 
        ["B1", "BI", "BL", "L20"], 
        ["G1", "GI", "GL", "L21", "L2I", "L2L"], 
        ["TE1", "TEI", "TEL", "L22"], 
        ["TCC1", "TCCI", "TCCL", "L23"], 
        ["L24"], 
        ["LUNCH"], 
        ["D2", "L49"], 
        ["B2", "L50"], 
        ["G2", "L51", "L5I", "L5L"], 
        ["TE2", "L52"]
    ],
    # FRIDAY
    [
        ["E1", "EI", "EL", "L25"], 
        ["C1", "CI", "CL", "L26"], 
        ["TA1", "TAI", "TAL", "L27"], 
        ["TF1", "TFI", "TFL", "L28"], 
        ["TDD1", "TDDI", "TDDL", "L29"], 
        ["L30", "S15", "SI5", "SL5"], 
        ["LUNCH"], 
        ["E2", "L55"], 
        ["C2", "L56"], 
        ["TA2", "L57"], 
        ["TF2", "L58"]
    ]
]

# Generate a flat set of all valid slot names to check against OCR text
ALL_KNOWN_SLOTS: Set[str] = set(
    slot for day in SLOT_TEMPLATE for timeslots in day for slot in timeslots if slot != "LUNCH"
)

# Configure PyTesseract
try:
    import pytesseract
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except ImportError:
    pytesseract = None

def is_ocr_available() -> bool:
    if pytesseract is None:
        return False
    return os.path.exists(TESSERACT_CMD) or bool(os.environ.get("TESSERACT_AVAILABLE", False))

def extract_slots_from_image(image_path: str) -> Dict[str, Any]:
    """
    Direct faithful implementation of extract_matrix_via_text from main.py.
    Extracts busy slots from VIT timetable screenshots using OpenCV cell isolation
    and PyTesseract cell-by-cell OCR.
    
    Database convention:
        matrix[d][t] = 1 (Busy)
        matrix[d][t] = 0 (Free)
    """
    # 5 days x 11 slots (0 = Free, 1 = Busy)
    matrix = [[0 for _ in range(11)] for _ in range(5)]
    found_busy_slots: Set[str] = set()

    if not os.path.exists(image_path):
        return {"success": False, "error": "Image file not found.", "matrix": matrix, "detected_slots": []}

    if not is_ocr_available():
        return {"success": False, "error": "Tesseract OCR engine not found at configured path.", "matrix": matrix, "detected_slots": []}

    try:
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": "Unable to decode image file.", "matrix": matrix, "detected_slots": []}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Grid detection purely to isolate text blocks (prevents OCR column-scrambling)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 4)
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))

        grid_mask = cv2.addWeighted(
            cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horiz_kernel), 0.5,
            cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vert_kernel), 0.5, 0
        )
        grid_mask = cv2.threshold(grid_mask, 0, 255, cv2.THRESH_BINARY)[1]
        contours, _ = cv2.findContours(grid_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # Pass 1: crop + preprocess every candidate cell
        cell_images = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if 200 < (w * h) < 200000 and w > 20 and h > 20:
                margin = 3
                cropped = img[y + margin : y + h - margin, x + margin : x + w - margin]
                if cropped.size == 0:
                    continue

                resized = cv2.resize(cropped, (0, 0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                cell_thresh = cv2.threshold(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                cell_images.append(cell_thresh)

        # Pass 2: OCR each candidate cell in parallel
        def _ocr_cell(cell_thresh):
            try:
                return pytesseract.image_to_string(cell_thresh, config='--psm 6').strip().upper()
            except Exception:
                return ""

        if cell_images:
            max_workers = min(16, len(cell_images))
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                for cell_text in pool.map(_ocr_cell, cell_images):
                    cleaned_text = " ".join(cell_text.split())

                    # EXACT main.py condition:
                    # If the block has text and looks like an actual course block (len > 8)
                    if len(cleaned_text) > 8:
                        # Scan the text for any known slot name using regex word boundaries
                        for known_slot in ALL_KNOWN_SLOTS:
                            if re.search(rf'\b{known_slot}\b', cleaned_text):
                                found_busy_slots.add(known_slot)

        # Cross-reference found slots with the master template to build the matrix
        LUNCH_TIME_INDEX = 6
        for d_idx, day_slots in enumerate(SLOT_TEMPLATE):
            for t_idx, time_slots in enumerate(day_slots):
                if t_idx == LUNCH_TIME_INDEX:
                    continue
                # If ANY of the slot names mapped to this specific time were found as busy
                if any(slot in found_busy_slots for slot in time_slots):
                    matrix[d_idx][t_idx] = 1  # 1 = Busy in database schema

        busy_count = sum(sum(row) for row in matrix)
        return {
            "success": True,
            "detected_slots": sorted(list(found_busy_slots)),
            "matrix": matrix,
            "busy_count": busy_count
        }

    except Exception as ex:
        return {
            "success": False,
            "error": f"Error processing timetable image: {str(ex)}",
            "matrix": matrix,
            "detected_slots": []
        }
