import uvicorn
from backend.app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("        🚀 AI FACT CHECKER IS STARTING...        ")
    print("=" * 60)
    print(f"Server manzili:  http://{settings.HOST}:{settings.PORT}")
    print(f"API Hujjatlari:  http://{settings.HOST}:{settings.PORT}/docs")
    print(f"Gemini Modeli:   {settings.GEMINI_MODEL}")
    print(f"Gemini Kaliti:   {'Sozlangan ✅' if settings.GEMINI_API_KEY else 'Kiritilmagan ⚠️ (Heuristic Fallback rejimida)'}")
    print("=" * 60)

    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )

