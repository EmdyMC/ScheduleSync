import cv2
import numpy as np
import pytesseract
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 1. THE HARDCODED SLOT TEMPLATE (Mon-Fri, 8:00 AM - 6:00 PM)
# Each cell contains a list of standard slot names that belong to that day/time.
# (You can easily edit these strings to perfectly match your university's exact slot codes)
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
ALL_KNOWN_SLOTS = set(slot for day in SLOT_TEMPLATE for timeslots in day for slot in timeslots)

def extract_matrix_via_text(image_path: str, name: str):
    # Initialize a 5x11 matrix of 1s (Everyone is Free by default)
    person_matrix = np.ones((5, 11))
    
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Still use grid detection purely to isolate text blocks (prevents OCR column-scrambling)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 4)
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 25))
    
    grid_mask = cv2.addWeighted(
        cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horiz_kernel), 0.5, 
        cv2.morphologyEx(thresh, cv2.MORPH_OPEN, vert_kernel), 0.5, 0
    )
    grid_mask = cv2.threshold(grid_mask, 0, 255, cv2.THRESH_BINARY)[1]
    contours, _ = cv2.findContours(grid_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # --- Pass 1 (fast, sequential): crop + preprocess every candidate cell ---
    # Pure numpy/OpenCV work - nothing to gain from threading it.
    # The real bottleneck is the tesseract subprocess call below.
    cell_images = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if 200 < (w * h) < 200000 and w > 20 and h > 20:
            margin = 3
            cropped = img[y+margin : y+h-margin, x+margin : x+w-margin]
            if cropped.size == 0:
                continue

            resized = cv2.resize(cropped, (0, 0), fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            cell_thresh = cv2.threshold(cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
            cell_images.append(cell_thresh)

    # --- Pass 2 (slow, parallel): OCR each candidate cell ---
    # pytesseract shells out to the tesseract binary as a subprocess, so it releases
    # the GIL while waiting - a thread pool gives real parallelism here.
    def _ocr_cell(cell_thresh):
        try:
            return pytesseract.image_to_string(cell_thresh, config='--psm 6').strip().upper()
        except Exception:
            return ""

    found_busy_slots = set()
    if cell_images:
        max_workers = min(16, len(cell_images))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            for cell_text in pool.map(_ocr_cell, cell_images):
                cleaned_text = " ".join(cell_text.split())

                # If the block has text and looks like an actual course block
                if len(cleaned_text) > 8:
                    # Scan the text for any known slot name using regex word boundaries
                    for known_slot in ALL_KNOWN_SLOTS:
                        if re.search(rf'\b{known_slot}\b', cleaned_text):
                            found_busy_slots.add(known_slot)

    # Cross-reference found slots with the master template to build the matrix
    for d_idx, day_slots in enumerate(SLOT_TEMPLATE):
        for t_idx, time_slots in enumerate(day_slots):
            # If ANY of the slot names mapped to this specific time were found as busy in the OCR scan
            if any(slot in found_busy_slots for slot in time_slots):
                person_matrix[d_idx, t_idx] = 0  # Mark as Busy
                
    print(f"   Successfully mapped matrix for {name}.")
    return person_matrix

def process_timetables(folder_path: str):
    if not os.path.exists(folder_path):
        return None

    image_files = [
        f for f in os.listdir(folder_path)
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    if not image_files:
        return {}

    all_schedules = {}
    start = time.time()

    # Each person's image is independent, and extract_matrix_via_text spends almost
    # all its time waiting on tesseract subprocess calls, so images are processed
    # concurrently rather than one after another.
    max_workers = min(8, len(image_files))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_name = {}
        for filename in image_files:
            name, _ = os.path.splitext(filename)
            print(f"-- Queuing {name}...")
            future = pool.submit(extract_matrix_via_text, os.path.join(folder_path, filename), name)
            future_to_name[future] = name

        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                all_schedules[name] = future.result()
            except Exception as e:
                print(f"   ! Failed to process {name}: {e}")

    print(f"Processed {len(all_schedules)} timetable(s) in {time.time() - start:.1f}s "
          f"({max_workers} worker threads).")
    return all_schedules

def generate_heatmap(combined_results: dict):
    import textwrap

    days = ["MON", "TUE", "WED", "THU", "FRI"]
    time_slots = [
        "08:00", "08:55", "09:50", "10:45", "11:40",
        "12:35", "Lunch", "14:00", "14:55", "15:50", "16:45"
    ]

    names = list(combined_results.keys())
    total_people = len(names)

    # Free-count matrix (for coloring) and per-cell list of busy people (for labels)
    heatmap_matrix = np.zeros((5, 11))
    busy_names_grid = [[[] for _ in range(11)] for _ in range(5)]
    for name, matrix in combined_results.items():
        heatmap_matrix += matrix
        for d in range(5):
            for t in range(11):
                if matrix[d, t] == 0:
                    busy_names_grid[d][t].append(name)

    people_str = ", ".join(names)

    # --- Style ---
    plt.rcParams["font.family"] = "sans-serif"
    fig, ax = plt.subplots(figsize=(16, 7.5))

    # Smooth, calmer red -> amber -> green gradient
    colors = ["#e04b4b", "#f2a93c", "#f5d76e", "#8fd35c", "#3fb950"]
    cmap = mcolors.LinearSegmentedColormap.from_list("availability", colors, N=256)

    im = ax.imshow(heatmap_matrix, cmap=cmap, aspect="auto", vmin=0, vmax=total_people)

    # Gridlines between cells for a cleaner, table-like look
    ax.set_xticks(np.arange(-0.5, 11, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, 5, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2.5)
    ax.tick_params(which="minor", bottom=False, left=False)

    # Cell labels: free count on top, busy names (wrapped) below
    for d in range(5):
        for t in range(11):
            free_count = int(heatmap_matrix[d, t])
            bg_frac = free_count / total_people if total_people else 0
            text_color = "white" if bg_frac < 0.3 or bg_frac > 0.9 else "#222222"

            busy = busy_names_grid[d][t]
            if time_slots[t] == "Lunch":
                sub_text = textwrap.fill(", ".join(busy), width=14)
            elif not busy:
                sub_text = "all free"
            elif len(busy) == total_people:
                sub_text = "all busy"
            else:
                sub_text = textwrap.fill(", ".join(busy), width=14)

            ax.text(t, d - 0.25, f"{free_count}/{total_people}",
                     ha="center", va="center", color=text_color,
                     fontweight="bold", fontsize=11)
            if sub_text:
                ax.text(t, d + 0.15, sub_text,
                         ha="center", va="center", color=text_color,
                         fontsize=7.5, linespacing=1.3)

    cbar = fig.colorbar(im, ax=ax, ticks=range(total_people + 1), pad=0.015)
    cbar.set_label("Number of People Free", rotation=270, labelpad=18, fontsize=12, fontweight="bold")
    cbar.outline.set_visible(False)

    ax.xaxis.tick_top()
    ax.xaxis.set_label_position("top")
    ax.set_xticks(range(11))
    ax.set_xticklabels(time_slots, fontsize=10.5, rotation=15)
    ax.set_yticks(range(5))
    ax.set_yticklabels(days, fontsize=11, fontweight="bold")

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title(f"Group Free Time Heatmap\n{people_str}",
                 fontsize=15, pad=22, fontweight="bold")

    plt.tight_layout()
    plt.savefig("group_heatmap.png", dpi=300, bbox_inches="tight")
    plt.show()

# --- RUN ---
folder = 'timetables'
results = process_timetables(folder)
if results:
    generate_heatmap(results)