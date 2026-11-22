import sys
from pathlib import Path
from fastapi import Request

# Add project root and backend to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.main import app

# Ensure all routes work both with and without /api prefix
existing_paths = {r.path for r in app.routes if hasattr(r, "path")}

for route in list(app.routes):
    p = getattr(route, "path", "")
    if p.startswith("/api/"):
        alt_path = p[4:]  # '/api/overview' -> '/overview'
        if alt_path not in existing_paths:
            existing_paths.add(alt_path)
            app.add_api_route(
                alt_path,
                route.endpoint,
                methods=getattr(route, "methods", ["GET"]),
                response_model=getattr(route, "response_model", None),
                include_in_schema=False
            )
