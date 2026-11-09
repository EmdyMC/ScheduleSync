-- ==============================================================================
-- ScheduleSync - Supabase PostgreSQL Production Schema
-- Designed for Supabase / PostgreSQL 14+
-- ==============================================================================

-- 1. USERS TABLE
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    reg_no VARCHAR(20) UNIQUE,
    campus VARCHAR(50) DEFAULT 'VIT Chennai',
    avatar_color VARCHAR(20) DEFAULT '#2563eb',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. TIMETABLES TABLE
CREATE TABLE IF NOT EXISTS timetables (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    semester VARCHAR(50) NOT NULL DEFAULT 'Winter Semester 2026',
    title VARCHAR(100) DEFAULT 'My Academic Schedule',
    is_active SMALLINT NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    original_image_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. TIMETABLE_SLOTS TABLE (Normalized Matrix Cells)
-- 5 days (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri) x 11 time slots (0..10)
CREATE TABLE IF NOT EXISTS timetable_slots (
    id SERIAL PRIMARY KEY,
    timetable_id INTEGER NOT NULL REFERENCES timetables(id) ON DELETE CASCADE,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 4),
    time_index SMALLINT NOT NULL CHECK (time_index BETWEEN 0 AND 10),
    is_busy SMALLINT NOT NULL DEFAULT 0 CHECK (is_busy IN (0, 1)),
    slot_code VARCHAR(20),
    course_name VARCHAR(100),
    UNIQUE (timetable_id, day_of_week, time_index)
);

-- 4. FRIENDSHIPS TABLE
CREATE TABLE IF NOT EXISTS friendships (
    id SERIAL PRIMARY KEY,
    sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (sender_id, receiver_id),
    CHECK (sender_id != receiver_id)
);

-- 5. GROUPS TABLE
CREATE TABLE IF NOT EXISTS groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    invite_code VARCHAR(12) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. GROUP_MEMBERS TABLE
CREATE TABLE IF NOT EXISTS group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('admin', 'member')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (group_id, user_id)
);

-- 7. SHARE_LINKS TABLE
CREATE TABLE IF NOT EXISTS share_links (
    id SERIAL PRIMARY KEY,
    token VARCHAR(64) UNIQUE NOT NULL,
    title VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
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
CREATE OR REPLACE VIEW v_user_friends AS
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
CREATE OR REPLACE VIEW v_active_slots AS
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
CREATE OR REPLACE VIEW v_group_members_details AS
SELECT 
    gm.id AS membership_id,
    gm.group_id,
    g.name AS group_name,
    g.invite_code,
    u.id AS user_id,
    u.username,
    u.full_name,
    u.reg_no,
    u.campus,
    u.avatar_color,
    gm.role,
    gm.joined_at
FROM group_members gm
JOIN groups g ON gm.group_id = g.id
JOIN users u ON gm.user_id = u.id;
