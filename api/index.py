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

# Duplicating routes without '/api' prefix as well, so requests work regardless of how Vercel rewrites them
for route in list(app.routes):
    if hasattr(route, "path") and route.path.startswith("/api/"):
        alt_path = route.path[4:]  # e.g. '/api/health' -> '/health', '/api/overview' -> '/overview'
        # Add alias route
        if hasattr(route, "methods"):
            app.add_api_route(
                alt_path,
                route.endpoint,
                methods=route.methods,
                response_model=getattr(route, "response_model", None),
                include_in_schema=False
            )

@app.get("/api/debug")
@app.get("/debug")
def debug_endpoint(request: Request):
    return {
        "url_path": request.url.path,
        "scope_path": request.scope.get("path"),
        "root_path": request.scope.get("root_path")
    }
