from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    reg_no: Optional[str] = Field(None, max_length=20)
    campus: Optional[str] = "VIT Chennai"
    avatar_color: Optional[str] = "#4f46e5"

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    reg_no: Optional[str] = None
    campus: Optional[str] = None
    avatar_color: Optional[str] = None

class SlotItem(BaseModel):
    day_of_week: int = Field(..., ge=0, le=4)
    time_index: int = Field(..., ge=0, le=10)
    is_busy: int = Field(..., ge=0, le=1)
    slot_code: Optional[str] = None
    course_name: Optional[str] = None

class TimetableUpdate(BaseModel):
    slots: List[SlotItem]
    semester: Optional[str] = "Winter Semester 2026"
    title: Optional[str] = "My Academic Schedule"

class FriendRequestAction(BaseModel):
    target_user_id: int

class FriendResponseAction(BaseModel):
    friendship_id: int
    action: str = Field(..., pattern="^(accepted|rejected)$")

class CreateGroupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None

class JoinGroupRequest(BaseModel):
    invite_code: str = Field(..., min_length=4, max_length=12)

class CreateShareLinkRequest(BaseModel):
    title: str = Field(default="Group Free Time Heatmap")
    group_id: Optional[int] = None
    user_id: Optional[int] = None
    expires_in_days: Optional[int] = 30

class ExecuteSqlRequest(BaseModel):
    sql: str
