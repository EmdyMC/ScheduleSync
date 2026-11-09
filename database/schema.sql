-- ==============================================================================
-- ScheduleSync Relational Database Schema
-- Academic Timetable Aggregator & Common Free Time Analyzer
-- ==============================================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------------------------
-- 1. USERS TABLE
-- Stores authenticated student accounts, profiles, and VIT credentials
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    reg_no VARCHAR(20) UNIQUE,
    campus VARCHAR(50) DEFAULT 'VIT Chennai',
    avatar_color VARCHAR(20) DEFAULT '#4f46e5',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- 2. TIMETABLES TABLE
-- Stores timetable metadata for each user (supports multiple semesters)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS timetables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    semester VARCHAR(50) NOT NULL DEFAULT 'Winter Semester 2026',
    title VARCHAR(100) DEFAULT 'My Academic Schedule',
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    original_image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 3. TIMETABLE_SLOTS TABLE (Normalized Matrix Cells)
-- 5 days (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri) x 11 time slots (0..10)
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS timetable_slots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timetable_id INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 4),
    time_index INTEGER NOT NULL CHECK (time_index BETWEEN 0 AND 10),
    is_busy INTEGER NOT NULL DEFAULT 0 CHECK (is_busy IN (0, 1)),
    slot_code VARCHAR(20),
    course_name VARCHAR(100),
    FOREIGN KEY (timetable_id) REFERENCES timetables(id) ON DELETE CASCADE,
    UNIQUE (timetable_id, day_of_week, time_index)
);

-- ------------------------------------------------------------------------------
-- 4. FRIENDSHIPS TABLE
-- Self-referential Many-to-Many social relationship between students
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS friendships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER NOT NULL,
    receiver_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (sender_id, receiver_id),
    CHECK (sender_id != receiver_id)
);

-- ------------------------------------------------------------------------------
-- 5. GROUPS TABLE
-- Project teams, study circles, and lab batches
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL,
    invite_code VARCHAR(12) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------------------------
-- 6. GROUP_MEMBERS TABLE
-- Many-to-Many junction table linking users to groups with authorization roles
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS group_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (group_id, user_id)
);

-- ------------------------------------------------------------------------------
-- 7. SHARE_LINKS TABLE
-- Secure token-based sharing of individual or group availability heatmaps
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS share_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(100) NOT NULL,
    user_id INTEGER,
    group_id INTEGER,
    created_by INTEGER NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

-- ==============================================================================
-- INDEXES FOR QUERY OPTIMIZATION
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_slots_lookup 
    ON timetable_slots(timetable_id, day_of_week, time_index, is_busy);

CREATE INDEX IF NOT EXISTS idx_active_timetable 
    ON timetables(user_id, is_active);

CREATE INDEX IF NOT EXISTS idx_friendship_lookup 
    ON friendships(sender_id, receiver_id, status);

CREATE INDEX IF NOT EXISTS idx_group_members_user 
    ON group_members(user_id, group_id);

CREATE INDEX IF NOT EXISTS idx_group_invite 
    ON groups(invite_code);

CREATE INDEX IF NOT EXISTS idx_share_token 
    ON share_links(token);

-- ==============================================================================
-- DATABASE VIEWS
-- ==============================================================================

-- VIEW 1: Bidirectional Accepted Friendships
-- Simplifies querying friends regardless of who sent the friend request
DROP VIEW IF EXISTS v_user_friends;
CREATE VIEW v_user_friends AS
SELECT 
    f.id AS friendship_id,
    f.sender_id AS user_id,
    u.id AS friend_id,
    u.username AS friend_username,
    u.full_name AS friend_full_name,
    u.reg_no AS friend_reg_no,
    u.campus AS friend_campus,
    u.avatar_color AS friend_avatar_color,
    f.created_at AS friendship_date
FROM friendships f
JOIN users u ON f.receiver_id = u.id
WHERE f.status = 'accepted'
UNION ALL
SELECT 
    f.id AS friendship_id,
    f.receiver_id AS user_id,
    u.id AS friend_id,
    u.username AS friend_username,
    u.full_name AS friend_full_name,
    u.reg_no AS friend_reg_no,
    u.campus AS friend_campus,
    u.avatar_color AS friend_avatar_color,
    f.created_at AS friendship_date
FROM friendships f
JOIN users u ON f.sender_id = u.id
WHERE f.status = 'accepted';

-- VIEW 2: Active Timetable Slots with Student Information
-- Flattens user information with their active busy slots for quick heatmap joins
DROP VIEW IF EXISTS v_active_slots;
CREATE VIEW v_active_slots AS
SELECT 
    u.id AS user_id,
    u.username,
    u.full_name,
    u.reg_no,
    t.id AS timetable_id,
    t.semester,
    s.day_of_week,
    s.time_index,
    s.is_busy,
    s.slot_code,
    s.course_name
FROM users u
JOIN timetables t ON u.id = t.user_id AND t.is_active = 1
JOIN timetable_slots s ON t.id = s.timetable_id;

-- VIEW 3: Group Member Directory with Roles and Profile Info
DROP VIEW IF EXISTS v_group_members_details;
CREATE VIEW v_group_members_details AS
SELECT 
    gm.group_id,
    g.name AS group_name,
    g.invite_code,
    gm.user_id,
    u.username,
    u.full_name,
    u.reg_no,
    u.avatar_color,
    gm.role,
    gm.joined_at,
    t.id AS active_timetable_id
FROM group_members gm
JOIN groups g ON gm.group_id = g.id
JOIN users u ON gm.user_id = u.id
LEFT JOIN timetables t ON u.id = t.user_id AND t.is_active = 1;

-- ==============================================================================
-- DATABASE TRIGGERS
-- ==============================================================================

-- TRIGGER 1: Automatically update updated_at timestamp when timetable is modified
DROP TRIGGER IF EXISTS trg_timetable_updated_at;
CREATE TRIGGER trg_timetable_updated_at
AFTER UPDATE ON timetables
FOR EACH ROW
BEGIN
    UPDATE timetables SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
END;

-- TRIGGER 2: Prevent a student from sending a friend request to themselves
DROP TRIGGER IF EXISTS trg_prevent_self_friendship;
CREATE TRIGGER trg_prevent_self_friendship
BEFORE INSERT ON friendships
FOR EACH ROW
WHEN NEW.sender_id = NEW.receiver_id
BEGIN
    SELECT RAISE(ABORT, 'A user cannot send a friend request to themselves.');
END;
