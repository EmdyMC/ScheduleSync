import uvicorn
import os
import sys

# Set stdout to UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"Starting ScheduleSync at http://{host}:{port}")
    print(f"API documentation: http://{host}:{port}/docs")
    from app.main import app
    uvicorn.run(app, host=host, port=port)
