import re
from urllib.parse import urlparse
from typing import Tuple
from ..models.schemas import SourceTypeEnum


class SourceAnalyzer:
    """Manbalarni tahlil qilish va ishonchlilik darajasini aniqlash.
    Domen kategoriyasi, TLD, SSL va matn signallarini tahlil qiladi.
    """

    # Existing hard‑coded sets (kept for backward compatibility)
    OFFICIAL_GOV_DOMAINS = {
        "gov.uz",
        "lex.uz",
        "president.uz",
        "gov",
        "gov.uk",
        "europa.eu",
        "parliament.gov.uz",
        "stat.uz",
        "ddo.uz",
        "edu.uz",
        "minzdrav.uz",
        "mfa.uz",
        "mvd.uz",
        "customs.uz",
        "soliq.uz",
        "adliya.uz",
    }

    # ------------------------------------------------------------
    # New configurable domain whitelists for Uzbek sources
    # ------------------------------------------------------------
    # Primary / Official sources – higher base credibility
    _PRIMARY_DEFAULT = {
        "lex.uz",
        "gov.uz",
        "president.uz",
        "stat.uz",
        "cbu.uz",
        "edu.uz",
        "uza.uz",
    }
    # Secondary / Independent media – medium credibility
    _SECONDARY_DEFAULT = {
        "kun.uz",
        "daryo.uz",
        "gazeta.uz",
        "qalampir.uz",
        "zamin.uz",
        "zamon.uz",
    }

    @classmethod
    def load_domain_overrides(cls):
        """Load primary/secondary domain whitelists from environment variables.
        Called at import time and can be re‑invoked after monkey‑patching.
        """
        import os
        env_primary = os.getenv("PRIMARY_SOURCES")
        env_secondary = os.getenv("SECONDARY_SOURCES")
        cls.PRIMARY_DOMAINS = set(cls._PRIMARY_DEFAULT)
        cls.SECONDARY_DOMAINS = set(cls._SECONDARY_DEFAULT)
        if env_primary:
            cls.PRIMARY_DOMAINS.update({d.strip().lower() for d in env_primary.split(",") if d.strip()})
        if env_secondary:
            cls.SECONDARY_DOMAINS.update({d.strip().lower() for d in env_secondary.split(",") if d.strip()})

    # Additional domain groups used by the original heuristic
    ACADEMIC_DOMAINS = {
        "edu",
        "edu.uz",
        "nature.com",
        "sciencedirect.com",
        "nih.gov",
        "ncbi.nlm.nih.gov",
        "arxiv.org",
        "ieee.org",
        "springer.com",
        "scholar.google.com",
        "jstor.org",
        "ox.ac.uk",
        "cam.ac.uk",
        "mit.edu",
        "harvard.edu",
    }

    FACT_CHECK_DOMAINS = {
        "snopes.com",
        "factcheck.org",
        "politifact.com",
        "fullfact.org",
        "factchecknet.uz",
        "daryo.uz",
        "reuters.com",
        "apnews.com",
    }

    MAJOR_NEWS_DOMAINS = {
        "kun.uz",
        "gazeta.uz",
        "daryo.uz",
        "podrobno.uz",
        "spot.uz",
        "qalampir.uz",
        "bbc.com",
        "reuters.com",
        "apnews.com",
        "dw.com",
        "euronews.com",
        "theguardian.com",
        "nytimes.com",
        "bloomberg.com",
        "aljazeera.com",
        "tass.ru",
        "ria.ru",
        "rbc.ru",
        "kommersant.ru",
        "interfax.ru",
    }

    REFERENCE_DOMAINS = {
        "wikipedia.org",
        "britannica.com",
        "who.int",
        "un.org",
        "unesco.org",
        "worldbank.org",
        "imf.org",
        "oecd.org",
    }

    LOW_RELIABILITY_DOMAINS = {
        "tiktok.com",
        "instagram.com",
        "facebook.com",
        "t.me",
        "telegram.org",
        "reddit.com",
        "twitter.com",
        "x.com",
        "blogspot.com",
        "wordpress.com",
        "pin.it",
        "vk.com",
        "ok.ru",
    }

    # E-commerce, online stores, classified ads & marketplace domains
    COMMERCIAL_DOMAINS = {
        "olx.uz", "uzum.uz", "olcha.uz", "ispace.uz", "asaxiy.uz", "mediapark.uz", "texnomart.uz",
        "birbir.uz", "zoodmall.uz", "aliexpress.com", "aliexpress.ru", "amazon.com", "ebay.com",
        "wildberries.ru", "market.yandex.ru", "avito.ru", "market.beeline.uz", "beemarket.uz",
        "glotr.uz", "tiu.ru", "macbro.uz", "openmall.uz", "sello.uz", "prom.uz", "bazar.uz",
        "alifshop.uz", "joybox.uz", "kasta.ua", "rozetka.com.ua", "ozon.ru", "mvideo.ru",
        "eldorado.ru", "dns-shop.ru", "sulpak.kz", "technodom.kz", "shop.uz", "mobimarket.uz",
        "torg.uz", "olx.kz", "olx.ua", "schetchik.uz",
    }

    @classmethod
    def is_commercial_or_marketplace(cls, url: str, domain: str = "", title: str = "") -> bool:
        """Klassifikatsiya: do'konlar, e'lonlar doskalari va marketpleyslarni aniqlaydi."""
        dom = (domain or cls.extract_domain(url)).lower()
        if cls._in(dom, cls.COMMERCIAL_DOMAINS):
            return True
        # Domain name contains shop, market, bazar, mall
        if any(part in dom for part in ["shop", "market", "bazar", "store"]):
            return True
        # URL path or title shopping indicators
        u_lower = url.lower()
        t_lower = (title or "").lower()
        shop_markers = [
            "/category/", "/product/", "/katalog/", "/kupit-", "/sotib-olish",
            "q-ishlatilgan", "/tovar/", "narxi", "купить смартфон", "цены на"
        ]
        if any(m in u_lower for m in shop_markers) or any(m in t_lower for m in ["купить", "sotib olish", "narxi"]):
            # Agar yangiliklar sayti bo'lmasa
            if not cls._in(dom, cls.MAJOR_NEWS_DOMAINS) and not cls._in(dom, cls.OFFICIAL_GOV_DOMAINS):
                return True
        return False

    # Sensationalist and clickbait keywords in Uzbek, Russian, English
    SENSATIONAL_PATTERNS = [
        r'\bshok\b', r'\bdahshat\b', r'\b100%\b', r'\bsensatsiya\b', r'\bhech kim bilmaydi\b',
        r'\bшокирующ', r'\bшок\b', r'\bсенсация\b', r'\bшок контент\b',
        r'\bshocking\b', r'\bmiracle\b', r'\bsecret revealed\b', r"\byou won\'t believe\b",
    ]

    @staticmethod
    def _in(domain: str, names) -> bool:
        """Aniq moslik: domen ro'yxatdagi nomning o'zi yoki uning subdomeni bo'lishi kerak ('x.com' 'dropbox.com' ga mos kelmaydi)."""
        return any(domain == n or domain.endswith("." + n) for n in names)

    @classmethod
    def extract_domain(cls, url: str) -> str:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return "unknown"

    @classmethod
    def classify_source(cls, url: str, title: str = "", excerpt: str = "") -> Tuple[SourceTypeEnum, float, str]:
        """Classify a source and compute a credibility score.

        Returns (source_type, reliability_score, label). The score is bounded
        between 0.10 and 0.95 and never automatically set to 1.0.
        """
        domain = cls.extract_domain(url)
        content_text = f"{title} {excerpt}".lower()

        # Default classification
        source_type = SourceTypeEnum.GENERAL_WEB
        base_score = 0.50

        # Primary official sources
        if cls._in(domain, getattr(cls, "PRIMARY_DOMAINS", set())) or cls._in(domain, cls.OFFICIAL_GOV_DOMAINS):
            source_type = SourceTypeEnum.OFFICIAL_GOVERNMENT
            base_score = 0.88
        # Secondary independent media
        elif cls._in(domain, getattr(cls, "SECONDARY_DOMAINS", set())):
            source_type = SourceTypeEnum.MAJOR_NEWS
            base_score = 0.78
        # Fact‑check organisations
        elif cls._in(domain, cls.FACT_CHECK_DOMAINS) and ("fact" in domain or "factcheck" in url.lower() or domain in {"snopes.com", "politifact.com", "fullfact.org"}):
            source_type = SourceTypeEnum.FACT_CHECK_ORG
            base_score = 0.90
        # Academic & scientific
        elif cls._in(domain, cls.ACADEMIC_DOMAINS) or domain.endswith('.edu.uz') or domain.endswith('.edu'):
            source_type = SourceTypeEnum.ACADEMIC_RESEARCH
            base_score = 0.86
        # Reference / multilateral
        elif cls._in(domain, cls.REFERENCE_DOMAINS):
            source_type = SourceTypeEnum.REPUTABLE_REFERENCE
            base_score = 0.82
        # Major reputable news (including whitelist entries)
        elif cls._in(domain, cls.MAJOR_NEWS_DOMAINS):
            source_type = SourceTypeEnum.MAJOR_NEWS
            base_score = 0.78
        # Low reliability / UGC
        elif cls._in(domain, cls.LOW_RELIABILITY_DOMAINS):
            source_type = SourceTypeEnum.LOW_RELIABILITY
            base_score = 0.25

        # Sensationalism penalty
        sensational_count = sum(1 for p in cls.SENSATIONAL_PATTERNS if re.search(p, content_text))
        if sensational_count > 0:
            base_score -= min(0.20, sensational_count * 0.08)

        # Excerpt richness adjustment
        if len(excerpt.strip()) > 100:
            base_score += 0.04
        elif excerpt.strip() and len(excerpt.strip()) < 20:
            base_score -= 0.03

        # Bounding final score
        final_score = round(max(0.10, min(0.95, base_score)), 2)
        if final_score >= 0.75:
            label = "Yuqori (High)"
        elif final_score >= 0.45:
            label = "O'rtacha (Medium)"
        else:
            label = "Past (Low)"

        return source_type, final_score, label

# Initialise domain whitelists from environment (if any)
SourceAnalyzer.load_domain_overrides()
