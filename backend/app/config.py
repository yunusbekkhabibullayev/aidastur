import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env file (with override=True so edits to .env take effect immediately)
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)


class Settings:
    PROJECT_NAME: str = "AI Fact Checker"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Evidence-Based AI Fact-Checking Platform powered by Gemini API & Real Web Search"

    # API Keys (strictly from environment)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    # Optional third-party search keys (if using fallback)
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "").strip()
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "").strip()

    # Server settings
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Allowed Origins for CORS
    ALLOWED_ORIGINS_RAW: str = os.getenv("ALLOWED_ORIGINS", "*")

    @property
    def ALLOWED_ORIGINS(self) -> list[str]:
        if self.ALLOWED_ORIGINS_RAW == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

    # Limits and parameters
    MAX_INPUT_LENGTH: int = 5000
    MAX_CLAIMS_PER_INPUT: int = int(os.getenv("MAX_CLAIMS_PER_INPUT", "5"))
    MAX_SEARCH_RESULTS_PER_CLAIM: int = int(os.getenv("MAX_SEARCH_RESULTS_PER_CLAIM", "6"))
    SEARCH_TIMEOUT: int = int(os.getenv("SEARCH_TIMEOUT_SECONDS", "10"))


settings = Settings()

