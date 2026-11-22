import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models.schemas import FactCheckRequest, FactCheckResponse, OverviewResponse
from .pipeline.fact_checker import fact_checker_pipeline
from .pipeline.overview import overview_pipeline
from .pipeline.claim_extractor import claim_extractor
from .pipeline.search_engine import search_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"
)
logger = logging.getLogger("fact_checker.main")

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Frontend Path
FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled error at {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Ma'lumotni tekshirish vaqtida texnik xatolik yuz berdi. Iltimos, birozdan keyin qayta urinib ko'ring.",
            "detail": "Server xatosi xavfsizlik nuqtai nazaridan yashirildi."
        }
    )


# --- API Routes ---

@app.get("/api/health")
async def health_check():
    """Tizim holati va tayyorligini tekshirish."""
    gemini_ready = bool(settings.GEMINI_API_KEY)
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "gemini_api_configured": gemini_ready,
        "gemini_model": settings.GEMINI_MODEL,
        "environment": "production" if not settings.DEBUG else "development"
    }


@app.post("/api/check", response_model=FactCheckResponse)
async def check_fact(request: FactCheckRequest):
    """
    Asosiy Fact-Checking Endpointi:
    Kiritilgan matnni claim extraction, web search, source credibility,
    Gemini AI tahlili va reliability scoring orqali tekshiradi.
    """
    if len(request.text.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tekshirish uchun matn kiritilishi shart (kamida 3 belgi)."
        )

    if len(request.text) > settings.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Matn juda uzun. Maksimal ruxsat etilgan hajm: {settings.MAX_INPUT_LENGTH} belgi."
        )

    try:
        response = fact_checker_pipeline.process(request)
        return response
    except Exception as e:
        logger.error(f"Error in fact-checking pipeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fact-checking tahlil jarayonida xatolik yuz berdi. Iltimos, qayta urinib ko'ring."
        )


@app.post("/api/overview", response_model=OverviewResponse)
def overview(request: FactCheckRequest):
    """
    Google AI Overview uslubidagi javob: kirish gaplari + sarlavhali punktlar,
    har biri manbalarga bog'langan. Hukm (TRUE/FALSE) va ball yo'q.
    Oddiy `def`: bloklovchi tarmoq chaqiruvlari threadpool'da ishlaydi.
    """
    text = request.text.strip()
    if len(text) < 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Kamida 3 belgi kiriting.")
    if len(request.text) > settings.MAX_INPUT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Matn juda uzun. Maksimal hajm: {settings.MAX_INPUT_LENGTH} belgi.",
        )
    try:
        return overview_pipeline.process(request)
    except Exception as e:
        logger.error(f"Error in overview pipeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Javob tayyorlashda xatolik yuz berdi. Iltimos, qayta urinib ko'ring.",
        )


@app.post("/api/extract-claims")
async def extract_claims_endpoint(request: FactCheckRequest):
    """Faqat claim extraction bosqichini sinash uchun."""
    claims = claim_extractor.extract_claims(request.text, request.language or "uz")
    return {"claims": claims, "count": len(claims)}


@app.get("/api/search")
async def search_endpoint(query: str):
    """Real internet qidiruv natijalarini ko'rish uchun."""
    sources, fact_checks = search_engine.search_evidence(query)
    return {
        "query": query,
        "sources_count": len(sources),
        "sources": [s.model_dump() for s in sources],
        "previous_fact_checks": [fc.model_dump() for fc in fact_checks]
    }


# Mount Static Frontend
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    async def serve_index():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend index.html topilmadi."}

