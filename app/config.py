import os
import shutil
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Detect serverless environment (Netlify Functions, AWS Lambda, Vercel)
IS_SERVERLESS = bool(
    os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    or os.environ.get("NETLIFY")
    or os.environ.get("VERCEL")
)

# Database configuration: Supabase (PostgreSQL) or fallback to SQLite
raw_db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
if raw_db_url and raw_db_url.startswith("postgres://"):
    raw_db_url = "postgresql://" + raw_db_url[len("postgres://"):]

DATABASE_URL = raw_db_url
IS_POSTGRES = bool(DATABASE_URL and ("postgres" in DATABASE_URL))

# In serverless environments with SQLite fallback, root filesystem is read-only; use /tmp
if IS_SERVERLESS:
    default_db_path = "/tmp/schedulesync.db"
    default_upload_dir = Path("/tmp/schedulesync_uploads")
else:
    default_db_path = str(BASE_DIR / "schedulesync.db")
    default_upload_dir = BASE_DIR / "uploads"

DATABASE_PATH = os.environ.get("DATABASE_PATH", default_db_path)
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(default_upload_dir)))
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
SUPABASE_SCHEMA_PATH = BASE_DIR / "database" / "supabase_schema.sql"

# Create uploads directory if it does not exist
try:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Security & JWT Auth
SECRET_KEY = os.environ.get("SECRET_KEY", "schedulesync-production-jwt-key-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Intelligent Tesseract OCR Executable Detection (Windows, Linux, macOS, Container)
def _detect_tesseract_path() -> str:
    env_override = os.environ.get("TESSERACT_CMD")
    if env_override and os.path.exists(env_override):
        return env_override

    which_path = shutil.which("tesseract")
    if which_path:
        return which_path

    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
        "/opt/homebrew/bin/tesseract",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate

    return "tesseract"

TESSERACT_CMD = _detect_tesseract_path()

# VIT Academic Timetable Grid Layout (5 days x 11 time slots)
DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIME_SLOTS = [
    "08:00", "08:55", "09:50", "10:45", "11:40",
    "12:35", "Lunch", "14:00", "14:55", "15:50", "16:45"
]

TIME_RANGES = [
    "08:00 - 08:50", "08:55 - 09:45", "09:50 - 10:40", "10:45 - 11:35", "11:40 - 12:30",
    "12:35 - 13:25", "13:30 - 14:00", "14:00 - 14:50", "14:55 - 15:45", "15:50 - 16:40", "16:45 - 17:35"
]

LUNCH_INDEX = 6

# Exact Master Slot Template from main.py
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
