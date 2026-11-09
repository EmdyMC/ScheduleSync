import sys
import os
import json
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import init_db, get_db_context, fetch_one
from app.auth import hash_password
from app.config import SLOT_TEMPLATE, LUNCH_INDEX, DATABASE_PATH

BASE_DIR = Path(__file__).resolve().parent.parent
TIMETABLES_JSON = BASE_DIR / "database" / "precomputed_timetables.json"

# Demo students (First names only, no surnames)
DEMO_USERS = [
    {
        "username": "michael",
        "email": "michael@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Michael",
        "reg_no": "24BCE5259",
        "campus": "VIT Chennai",
        "avatar_color": "#2563eb"
    },
    {
        "username": "jack",
        "email": "jack@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Jack",
        "reg_no": "21BCE1002",
        "campus": "VIT Chennai",
        "avatar_color": "#0ea5e9"
    },
    {
        "username": "elena",
        "email": "elena@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Elena",
        "reg_no": "21BCE1003",
        "campus": "VIT Chennai",
        "avatar_color": "#ec4899"
    },
    {
        "username": "charis",
        "email": "charis@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Charis",
        "reg_no": "21BCE1004",
        "campus": "VIT Chennai",
        "avatar_color": "#10b981"
    },
    {
        "username": "ritika",
        "email": "ritika@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Ritika",
        "reg_no": "21BCE1005",
        "campus": "VIT Chennai",
        "avatar_color": "#8b5cf6"
    },
    {
        "username": "navaneeth",
        "email": "navaneeth@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Navaneeth",
        "reg_no": "21BCE1006",
        "campus": "VIT Chennai",
        "avatar_color": "#f59e0b"
    },
    {
        "username": "sanjeev",
        "email": "sanjeev@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Sanjeev",
        "reg_no": "21BCE1007",
        "campus": "VIT Chennai",
        "avatar_color": "#14b8a6"
    },
    {
        "username": "chaithanya",
        "email": "chaithanya@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Chaithanya",
        "reg_no": "21BCE1008",
        "campus": "VIT Chennai",
        "avatar_color": "#ef4444"
    },
    {
        "username": "lakkshanth",
        "email": "lakkshanth@vitstudent.ac.in",
        "password": "password123",
        "full_name": "Lakkshanth",
        "reg_no": "21BCE1009",
        "campus": "VIT Chennai",
        "avatar_color": "#6366f1"
    }
]

def load_ocr_matrices():
    """Load the pre-computed OCR matrices from JSON, or fallback to real-time OCR."""
    if os.path.exists(TIMETABLES_JSON):
        with open(TIMETABLES_JSON, "r") as f:
            return json.load(f)
    
    print("Precomputed timetable JSON not found. Running OCR on timetables/ folder...")
    import main
    raw_results = main.process_timetables(str(BASE_DIR / "timetables"))
    matrices = {}
    for name, mat in raw_results.items():
        # In main.py: 1 = Free, 0 = Busy. Convert to 1 = Busy, 0 = Free
        matrices[name] = (1 - mat).astype(int).tolist()
    return matrices

def seed_database(reset: bool = True):
    db_file = Path(DATABASE_PATH)
    if reset and db_file.exists():
        try:
            db_file.unlink()
        except Exception:
            pass

    # Ensure schema exists
    init_db()

    # If reset is False, check if data already exists
    if not reset:
        existing_user = fetch_one("SELECT id FROM users LIMIT 1;")
        if existing_user:
            return

    print("Seeding database with demo students and real OCR timetables...")
    ocr_matrices = load_ocr_matrices()
    user_id_map = {}

    with get_db_context() as conn:
        cursor = conn.cursor()

        # 1. Seed Users and Timetables with REAL OCR Data
        for u in DEMO_USERS:
            pw_hash = hash_password(u["password"])
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, reg_no, campus, avatar_color)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (u["username"], u["email"], pw_hash, u["full_name"], u["reg_no"], u["campus"], u["avatar_color"])
            )
            uid = cursor.lastrowid
            user_id_map[u["username"]] = uid

            # Associate original image path if it exists
            img_filename = f"{u['full_name']}.jpeg"
            img_path = f"timetables/{img_filename}" if (BASE_DIR / "timetables" / img_filename).exists() else None

            # Create active timetable
            cursor.execute(
                """
                INSERT INTO timetables (user_id, semester, title, is_active, original_image_path)
                VALUES (?, 'Winter Semester 2026', 'My Academic Schedule', 1, ?)
                """,
                (uid, img_path)
            )
            tt_id = cursor.lastrowid

            # Look up real OCR matrix
            # Matrix: 5 days x 11 slots (1 = Busy, 0 = Free)
            person_matrix = ocr_matrices.get(u["full_name"])
            if person_matrix is None:
                # Fallback to empty grid
                person_matrix = [[0 for _ in range(11)] for _ in range(5)]

            for d in range(5):
                for t in range(11):
                    is_busy = person_matrix[d][t]
                    code = "LUNCH" if t == LUNCH_INDEX else SLOT_TEMPLATE[d][t][0]
                    cursor.execute(
                        """
                        INSERT INTO timetable_slots (timetable_id, day_of_week, time_index, is_busy, slot_code)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (tt_id, d, t, is_busy, code)
                    )

        print(f"✅ Seeded {len(DEMO_USERS)} demo students with their ACTUAL OCR timetable matrices.")

        # 2. Seed Friendships
        m_id = user_id_map["michael"]
        friendships_to_add = [
            (m_id, user_id_map["jack"], "accepted"),
            (m_id, user_id_map["elena"], "accepted"),
            (m_id, user_id_map["charis"], "accepted"),
            (m_id, user_id_map["ritika"], "accepted"),
            (user_id_map["navaneeth"], m_id, "pending"),
            (m_id, user_id_map["sanjeev"], "pending"),
            (user_id_map["jack"], user_id_map["elena"], "accepted"),
            (user_id_map["jack"], user_id_map["chaithanya"], "accepted"),
            (m_id, user_id_map["lakkshanth"], "accepted")
        ]

        for s_id, r_id, status in friendships_to_add:
            cursor.execute(
                """
                INSERT OR IGNORE INTO friendships (sender_id, receiver_id, status)
                VALUES (?, ?, ?)
                """,
                (s_id, r_id, status)
            )
        print("✅ Seeded friendship social network relationships.")

        # 3. Seed Groups
        # Group 1: Core Study Group
        cursor.execute(
            """
            INSERT INTO groups (name, description, created_by, invite_code)
            VALUES ('Core Study Group', 'Collaborative timetable scheduler and project team', ?, 'STUDY4')
            """,
            (m_id,)
        )
        g1_id = cursor.lastrowid
        for member_name, role in [("michael", "admin"), ("jack", "member"), ("elena", "member"), ("charis", "member"), ("lakkshanth", "member")]:
            cursor.execute(
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)",
                (g1_id, user_id_map[member_name], role)
            )

        # Group 2: VIT Hackathon Squad
        cursor.execute(
            """
            INSERT INTO groups (name, description, created_by, invite_code)
            VALUES ('VIT Hackathon Squad', 'Cross-branch competitive coding & hackathon group', ?, 'HACK26')
            """,
            (m_id,)
        )
        g2_id = cursor.lastrowid
        for member_name, role in [("michael", "admin"), ("ritika", "member"), ("navaneeth", "member"), ("sanjeev", "member"), ("chaithanya", "member")]:
            cursor.execute(
                "INSERT OR IGNORE INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)",
                (g2_id, user_id_map[member_name], role)
            )

        print("Seeded groups with member rosters.")

        # 4. Seed a public Share Link
        cursor.execute(
            """
            INSERT INTO share_links (token, title, group_id, created_by)
            VALUES ('demo-team04', 'Core Study Group Availability Heatmap', 1, ?)
            """,
            (m_id,)
        )
        print("✅ Seeded demo share link (/share/demo-team04).")

    print("\n🎉 Database Seeding Complete! Real OCR timetable data is loaded.")

if __name__ == "__main__":
    seed_database()
