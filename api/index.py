import sys
from pathlib import Path
from starlette.types import ASGIApp, Scope, Receive, Send

# Add project root and backend to python path
ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.main import app as fastapi_app

# Also register non-prefixed routes as aliases (/overview, /check, /health)
existing_paths = {getattr(r, "path", "") for r in fastapi_app.routes}
for route in list(fastapi_app.routes):
    p = getattr(route, "path", "")
    if p.startswith("/api/"):
        alt_path = p[4:]
        if alt_path not in existing_paths:
            existing_paths.add(alt_path)
            fastapi_app.add_api_route(
                alt_path,
                route.endpoint,
                methods=getattr(route, "methods", ["GET"]),
                response_model=getattr(route, "response_model", None),
                include_in_schema=False
            )


class VercelMiddleware:
    """
    Vercel rewrites often set scope['path'] to the function filename (e.g. /api/index.py).
    This middleware extracts the true requested path from Vercel's 'x-matched-path'
    header or preserves the original /api/... path so FastAPI routes match 100%.
    """
    def __init__(self, inner: ASGIApp):
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))
            # Check for Vercel's matched path header (header keys in ASGI are lowercase bytes)
            matched_bytes = headers.get(b"x-matched-path") or headers.get(b"x-vercel-matched-path")
            if matched_bytes:
                matched_str = matched_bytes.decode("utf-8")
                # Strip query string if any
                if "?" in matched_str:
                    matched_str = matched_str.split("?")[0]
                scope["path"] = matched_str
            else:
                cur_path = scope.get("path", "")
                if cur_path == "/api/index.py" or cur_path == "/api":
                    # Fallback if matched path is missing
                    pass

        await self.inner(scope, receive, send)


app = VercelMiddleware(fastapi_app)
