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


class VercelPathNormalizer:
    """Normalizes incoming paths from Vercel so both /api/... and /... hit FastAPI routes cleanly."""
    def __init__(self, inner: ASGIApp):
        self.inner = inner

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope.get("type") == "http":
            path = scope.get("path", "")
            # If path does not start with /api, prefix it so FastAPI routes match
            if not path.startswith("/api"):
                scope["path"] = f"/api{path}"
        await self.inner(scope, receive, send)


app = VercelPathNormalizer(fastapi_app)
