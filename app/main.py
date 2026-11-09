import os
import shutil
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.config import (
    BASE_DIR,
    UPLOAD_DIR,
    DATABASE_PATH,
    IS_POSTGRES,
)
from app.database import init_db
from app.routers import (
    auth_router,
    timetable_router,
    friends_router,
    groups_router,
    compare_router,
    share_router,
)

# Initialize FastAPI application
app = FastAPI(
    title="ScheduleSync",
    description="VIT Academic Timetable Aggregator & Common Free Time Analyzer",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static and Upload directories
static_dir = BASE_DIR / "app" / "static"
templates_dir = BASE_DIR / "app" / "templates"

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

templates = Jinja2Templates(directory=str(templates_dir))

# Include API Routers
app.include_router(auth_router.router)
app.include_router(timetable_router.router)
app.include_router(friends_router.router)
app.include_router(groups_router.router)
app.include_router(compare_router.router)
app.include_router(share_router.router)


@app.on_event("startup")
def startup_event():
    """Ensure database schema is ready on startup."""
    if IS_POSTGRES:
        try:
            init_db()
        except Exception as e:
            print(f"PostgreSQL init notice: {e}")
    else:
        db_path = Path(DATABASE_PATH)
        bundle_db = BASE_DIR / "schedulesync.db"

        if not db_path.exists():
            if bundle_db.exists() and str(bundle_db.resolve()) != str(db_path.resolve()):
                try:
                    db_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(bundle_db), str(db_path))
                except Exception as e:
                    print(f"Note: Could not copy bundled DB: {e}")

            if not db_path.exists():
                print(f"Initializing database at {db_path}...")
                init_db()


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/share/{token}", response_class=HTMLResponse)
def share_page(request: Request, token: str):
    """Public shared heatmap page."""
    return templates.TemplateResponse(request=request, name="share.html", context={"token": token})
