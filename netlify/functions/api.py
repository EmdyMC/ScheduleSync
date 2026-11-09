import sys
from pathlib import Path

# Add project root to sys.path so app imports work seamlessly
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mangum import Mangum
from app.main import app

# Mangum converts AWS Lambda / Netlify Serverless events to ASGI requests
handler = Mangum(app, lifespan="off")
