import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.main import app

# Add aliases without /api prefix as well, just in case
existing_paths = {getattr(r, "path", "") for r in app.routes}
for route in list(app.routes):
    p = getattr(route, "path", "")
    if p.startswith("/api/"):
        alt = p[4:]
        if alt not in existing_paths:
            existing_paths.add(alt)
            app.add_api_route(
                alt,
                route.endpoint,
                methods=getattr(route, "methods", ["GET"]),
                response_model=getattr(route, "response_model", None),
                include_in_schema=False
            )
