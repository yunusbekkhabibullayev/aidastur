import re
import socket
import ipaddress
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from ..config import settings
from ..models.schemas import Source, PreviousFactCheck
from ..utils.text_utils import clean_text, latin_to_cyrillic, cyrillic_to_latin
from .source_analyzer import SourceAnalyzer

logger = logging.getLogger("fact_checker.search")

USER_AGENT = "Mozilla/5.0 (compatible; AIFactChecker/1.0)"
WIKI_LIMIT = 3                # har bir til uchun nechta Vikipediya maqolasi
STOPWORDS = {
    "bilan", "uchun", "va", "ham", "yoki", "lekin", "bu", "shu", "esa", "deb", "kabi", "emas",
    "etilgan", "qilingan", "bo'lgan", "bo\u2018lgan", "hisoblanadi", "yildan", "yilda",
    "barcha", "har", "bir", "qachon", "qanday", "nima", "qayerda", "oladi", "qiladi", "haqida", "kerak",
    "что", "это", "как", "для", "или", "был", "была", "было",
    "that", "this", "with", "from", "have", "were", "been", "which", "their",
}

GENERIC_LOCATION_WORDS = {
    "o'zbekiston", "o'zbekistonda", "o'zbekistonlik", "uzbekistan", "узбекистан", "узбекистане"
}

COMMON_MODIFIERS = {
    "eng", "mashhur", "katta", "kichik", "yangi", "eski", "bepul", "pullik", "arzon", "qimmat",
    "barcha", "hamma", "har", "bir", "birinchi", "oxirgi", "asosiy", "muhim", "top", "zo'r",
    "dunyodagi", "dunyo", "jahon", "xalqaro", "milliy", "davlat", "respublika",
    "sotib", "olish", "oladi", "beriladi", "qiladi", "bo'ldi", "bo'lgan", "o'ldi",
    "qachon", "qayerda", "qanday", "nima", "sabab", "haqida",
    "bilan", "uchun", "va", "ham", "yoki", "lekin", "bu", "shu", "esa", "deb", "kabi", "emas",
    "etilgan", "qilingan", "hisoblanadi", "yildan", "yilda",
    "o'zbekiston", "o'zbekistonda", "o'zbekistonlik", "uzbekistan", "узбекистан", "узбекистане"
}


def extract_core_subject_tokens(text: str) -> List[str]:
    """So'rovdagi asosiy sub'ekt va obyekt so'zlarini (entity/noun) ajratadi."""
    words = re.findall(r"[^\W\d_]+(?:['\u2018\u2019\u02bb\u02bc`][^\W\d_]+)*", text, flags=re.UNICODE)
    meaningful = [w for w in words if len(w) >= 3 and w.lower() not in STOPWORDS]
    distinctive = [w for w in meaningful if w.lower() not in GENERIC_LOCATION_WORDS]
    return distinctive if distinctive else meaningful


def extract_primary_subject_tokens(text: str) -> List[str]:
    """Modifikator, sifat va predikatlardan xoli eng muhim sub'ekt/obyekt otlari."""
    words = re.findall(r"[^\W\d_]+(?:['\u2018\u2019\u02bb\u02bc`][^\W\d_]+)*", text, flags=re.UNICODE)
    meaningful = [w.lower() for w in words if len(w) >= 3]
    primary = [w for w in meaningful if w not in COMMON_MODIFIERS]
    return primary if primary else meaningful


def is_multi_claim_query(query: str) -> bool:
    """So'rov bir nechta alohida gap/da'voni o'z ichiga oladimi?"""
    # Nuqta + bo'sh joy bilan ajratilgan ikki va undan ko'p gap = multi-claim
    sentences = [s.strip() for s in re.split(r'[.!?]+', query) if len(s.strip()) > 10]
    return len(sentences) >= 2


def is_source_relevant(query: str, title: str, excerpt: str, page_text: str = "") -> bool:
    """Manba berilgan so'rov yoki da'vo mazmuniga real bog'liq ekanligini tekshiradi.

    Multi-claim (bir nechta gapli) so'rovlarda yumshoq filtr (ANY token match).
    Single-claim so'rovlarda qat'iy filtr (kombinatsiyali token match).
    """
    target = f"{title} {excerpt} {page_text}".lower()

    def match_token(tok: str, text: str) -> bool:
        if tok in text:
            return True
        # O'zbek qo'shimchalarini inobatga olish
        if tok.endswith("lar") and len(tok) > 4 and tok[:-3] in text:
            return True
        if tok.endswith("ga") and len(tok) > 3 and tok[:-2] in text:
            return True
        if tok.endswith("da") and len(tok) > 3 and tok[:-2] in text:
            return True
        if tok.endswith("ning") and len(tok) > 5 and tok[:-4] in text:
            return True
        if tok.endswith("ni") and len(tok) > 3 and tok[:-2] in text:
            return True
        return False

    # Multi-claim (masalan: "Yer Quyosh atrofida aylanadi. Toshkent poytaxt hisoblanadi.")
    # Bunday so'rovlarda har bir gap o'z mavzusiga ega, shuning uchun
    # manba ILK CLAIM tokenlariga mos kelishi yetarli
    if is_multi_claim_query(query):
        # Har bir gap (claim) uchun alohida tekshiramiz: kamida 1 gapga tegishli bo'lsa qabul qilamiz
        sentences = [s.strip() for s in re.split(r'[.!?]+', query) if len(s.strip()) > 10]
        for sent in sentences:
            sent_primary = extract_primary_subject_tokens(sent)
            if not sent_primary:
                continue
            sent_matches = sum(1 for tok in sent_primary if match_token(tok, target))
            # Agar shu gapning asosiy tokenlaridan kamida 1 tasi manbada bo'lsa, maqbul
            if sent_matches >= 1:
                return True
        return False

    # Single-claim so'rov
    primary = extract_primary_subject_tokens(query)
    if not primary:
        return True

    matches = sum(1 for tok in primary if match_token(tok, target))
    # 2 va undan ko'p alohida sub'ekt bo'lsa (iPhone + talabalar), ikkisi ham bo'lsin
    if len(primary) >= 2:
        return matches >= 2
    return matches >= 1


def keyword_variants(text: str) -> List[str]:
    """
    Qidiruv tizimlari (Vikipediya, DuckDuckGo) uchun samarali kalit so'z kombinatsiyalarini tuzadi.
    Asosiy sub'ekt va obyektlarni (masalan: 'iPhone', 'begemot', 'Jizzax') hech qachon tushirib qoldirmaydi.
    """
    clean = re.sub(r'[";\']', '', text).strip()
    words = re.findall(r"[^\W\d_]+(?:['\u2018\u2019\u02bb\u02bc`][^\W\d_]+)*|\d+", clean, flags=re.UNICODE)
    meaningful = [w for w in words if len(w) >= 3 and w.lower() not in STOPWORDS]
    core = extract_core_subject_tokens(clean)

    variants: List[str] = []
    # 1. Asosiy mazmunli so'zlar
    if meaningful:
        v1 = " ".join(meaningful)
        if v1 not in variants:
            variants.append(v1)

    # 2. Asosiy mavzu sub'ektlari (iPhone, talabalar kabi)
    if core:
        v2 = " ".join(core)
        if v2 not in variants:
            variants.append(v2)

    # 3. Agar 3 tadan ko'p bo'lsa, eng muhim 3 ta entity
    if len(core) >= 3:
        v3 = " ".join(core[:3])
        if v3 not in variants:
            variants.append(v3)

    return variants


PAGE_FETCH_TOP_N = 4          # nechta eng ishonchli sahifadan to'liq matn olinadi
PAGE_MAX_BYTES = 300_000      # bitta sahifadan ko'pi bilan shuncha o'qiladi
PAGE_TEXT_CHARS = 2500        # Gemini'ga beriladigan matn uzunligi


def _is_public_http_url(url: str) -> bool:
    """SSRF himoyasi: faqat ommaviy http(s) manzillarga ruxsat."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return False
        for info in socket.getaddrinfo(parsed.hostname, None):
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                return False
        return True
    except Exception:
        return False


def fetch_page_text(url: str) -> Optional[str]:
    """Sahifaning asosiy matnini (paragraflar) oladi. Xato bo'lsa None."""
    if not _is_public_http_url(url):
        return None
    try:
        with requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
            timeout=settings.SEARCH_TIMEOUT / 2,
            stream=True,
            allow_redirects=True,
        ) as resp:
            if resp.status_code != 200:
                return None
            if "html" not in resp.headers.get("Content-Type", "").lower():
                return None
            # Redirectdan keyin ham ommaviy manzilligini tekshiramiz
            if resp.url != url and not _is_public_http_url(resp.url):
                return None
            raw = resp.raw.read(PAGE_MAX_BYTES, decode_content=True)
            encoding = resp.encoding or "utf-8"
        soup = BeautifulSoup(raw.decode(encoding, errors="ignore"), "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "li"])]
        text = " ".join(p for p in paragraphs if len(p) > 40)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:PAGE_TEXT_CHARS] or None
    except Exception as e:
        logger.debug(f"Page fetch failed for {url}: {e}")
        return None


class SearchEngine:
    """
    Real Web Search:
    1) Vikipediya rasmiy API'si (kalitsiz, barqaror, maqola matni bilan)
    2) DuckDuckGo (DDGS): avval to'liq so'rov, natija bo'lmasa qisqa kalit so'zlar bilan
    3) Manbalarni baholash (SourceAnalyzer)
    Soxta yoki oldindan yozilgan manbalar ishlatilmaydi.
    """

    def __init__(self):
        self.max_results = settings.MAX_SEARCH_RESULTS_PER_CLAIM

    # ---------- Source yasash ----------
    def _make_source(self, url: str, title: str, body: str, page_text: Optional[str] = None,
                     image_url: Optional[str] = None) -> Source:
        source_type, reliability, label = SourceAnalyzer.classify_source(url, title, body)
        date_match = re.search(
            r'\b(19[8-9][0-9]|20[0-3][0-9])[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12][0-9]|3[01])\b', body or ""
        )
        return Source(
            source_title=title,
            source_url=url,
            source_domain=SourceAnalyzer.extract_domain(url),
            source_date=date_match.group(0) if date_match else None,
            source_excerpt=body or "",
            source_type=source_type,
            source_reliability=reliability,
            credibility_label=label,
            page_text=page_text,
            image_url=image_url,
        )

    # ---------- Vikipediya ----------
    def _wikipedia_search(self, query: str, lang: str) -> List[Source]:
        """Vikipediya API: qidiruv + maqola boshlanmasi bitta so'rovda."""
        try:
            resp = requests.get(
                f"https://{lang}.wikipedia.org/w/api.php",
                params={
                    "action": "query", "format": "json", "formatversion": 2,
                    "generator": "search", "gsrsearch": query, "gsrlimit": WIKI_LIMIT,
                    "prop": "extracts|info|pageimages", "pithumbsize": 300, "exintro": 1, "explaintext": 1,
                    "exchars": PAGE_TEXT_CHARS, "inprop": "url",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=settings.SEARCH_TIMEOUT,
            )
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", [])
        except Exception as e:
            logger.info(f"Wikipedia search note ({lang}): {e}")
            return []

        core_tokens = [t.lower() for t in extract_core_subject_tokens(query)]
        out: List[Source] = []
        for page in sorted(pages, key=lambda p: p.get("index", 0)):
            extract = (page.get("extract") or "").strip()
            url = page.get("fullurl") or ""
            title = page.get("title", "")
            if not extract or not url:
                continue
            if core_tokens:
                combined = f"{title} {extract}".lower()
                if not any(ct in combined for ct in core_tokens):
                    continue
            thumb = (page.get("thumbnail") or {}).get("source")
            out.append(self._make_source(url, title, extract[:400], page_text=extract, image_url=thumb))
        return out

    # ---------- DuckDuckGo ----------
    def _ddgs_search(self, query: str) -> List[dict]:
        try:
            from ddgs import DDGS
            safe_query = re.sub(r'[";\']', '', query).strip()
            with DDGS(timeout=settings.SEARCH_TIMEOUT) as ddgs:
                return list(ddgs.text(safe_query, max_results=self.max_results))
        except Exception as e:
            logger.info(f"Live web search note: {e}")
            return []

    def search_evidence(
        self, query: str, claim_text: str = "", use_wikipedia: bool = True, lang: str = "uz"
    ) -> Tuple[List[Source], List[PreviousFactCheck]]:
        sources: List[Source] = []
        fact_checks: List[PreviousFactCheck] = []
        seen_urls = set()

        def add(src: Source):
            if src.source_url not in seen_urls and src.source_url.lower().startswith(("http://", "https://")):
                seen_urls.add(src.source_url)
                sources.append(src)

        variants = keyword_variants(claim_text or query)

        # Multi-claim so'rovlarda (bir nechta gap) har bir gap uchun
        # alohida Wikipedia va DuckDuckGo qidiruvini ham qo'shamiz
        query_sentences = [s.strip() for s in re.split(r'[.!?]+', query) if len(s.strip()) > 10]
        per_sentence_queries: List[str] = []
        if len(query_sentences) >= 2:
            for sent in query_sentences:
                sent_core = extract_core_subject_tokens(sent)
                if sent_core:
                    per_sentence_queries.append(" ".join(sent_core[:3]))

        # 1) Vikipediya: avval da'vo tili, keyin inglizcha (maqolalar ko'proq)
        if use_wikipedia:
            wiki_langs = [lang] if lang == "en" else [lang, "en"]
            # Multi-claim uchun: har bir gap ALOHIDA qidiruv oladi (break yo'q)
            # Single-claim uchun: birinchi muvaffaqiyatli natijadan keyin to'xtaymiz
            is_multi = len(per_sentence_queries) >= 2

            if is_multi:
                # Har bir gap uchun alohida Wikipedia qidiruvi
                for sent_q in per_sentence_queries:
                    if not sent_q:
                        continue
                    for wl in wiki_langs:
                        found = self._wikipedia_search(sent_q, wl)
                        if found:
                            for src in found:
                                add(src)
                            break  # bu til uchun topildi, inglizcha kerak emas
                # Umumiy variantlardan ham qidiramiz (bonus)
                for v in variants[:1]:
                    if not v:
                        continue
                    for wl in wiki_langs:
                        found = self._wikipedia_search(v, wl)
                        if found:
                            for src in found:
                                add(src)
                            break
            else:
                # Single-claim: birinchi muvaffaqiyatli natijadan keyin to'xtaymiz
                all_wiki_queries = variants[:2]
                for wl in wiki_langs:
                    for v in all_wiki_queries:
                        if not v:
                            continue
                        found = self._wikipedia_search(v, wl)
                        if found:
                            for src in found:
                                add(src)
                            break

        # 2) DuckDuckGo: to'liq so'rov -> bo'lmasa qisqa variantlar
        # Multi-claim uchun har bir gap uchun ham alohida qidiruv
        search_queries = [query] + per_sentence_queries + variants[1:]
        # O'zbek tili uchun: agar so'rov lotinda bo'lsa kirill variantini ham qo'shamiz
        if lang == "uz":
            cyr_q = latin_to_cyrillic(query)
            if cyr_q != query:
                search_queries.append(cyr_q)

        results: List[dict] = []
        # Multi-claim uchun: birinchi to'liq so'rovni sinab ko'ramiz,
        # agar natija kam bo'lsa, har bir alohida gap uchun ham qidiruv qilamiz
        for q in search_queries:
            new_results = self._ddgs_search(q)
            # Allaqachon ko'rilgan URL'larni qo'shmaymiz
            existing_urls = {r.get("href", "") for r in results}
            for r in new_results:
                if r.get("href", "") not in existing_urls:
                    results.append(r)
                    existing_urls.add(r.get("href", ""))
            # Birinchi to'liq qidiruv yetarli natija bersa, to'xtaymiz
            if len(results) >= 5 and q == search_queries[0]:
                break
        for r in results:
            url = r.get("href") or r.get("url") or ""
            title = r.get("title") or ""
            body = r.get("body") or r.get("snippet") or ""
            if not url:
                continue
            dom = SourceAnalyzer.extract_domain(url)
            # Do'konlar, marketpleyslar va tijoriy e'lonlar sahifalarini o'tkazib yuboramiz
            if SourceAnalyzer.is_commercial_or_marketplace(url, dom, title):
                continue
            src = self._make_source(url, title, body)
            add(src)
            if "fact" in src.source_domain or "factcheck" in url.lower() or "fakt" in title.lower():
                fact_checks.append(PreviousFactCheck(
                    claim=claim_text or title, fact_checker=src.source_domain,
                    verdict="Mavjud tekshiruv", date=src.source_date, url=url,
                ))

        if not sources:
            logger.info("Hech qanday manba topilmadi (Vikipediya va DuckDuckGo bo'sh).")
        return sources, fact_checks

    def enrich_with_page_text(self, sources: List[Source]) -> None:
        """Matni hali yo'q, eng ishonchli manbalarning sahifasini parallel olib, page_text ga yozadi."""
        top = [s for s in sorted(sources, key=lambda s: s.source_reliability, reverse=True)[:PAGE_FETCH_TOP_N]
               if not s.page_text]
        if not top:
            return
        with ThreadPoolExecutor(max_workers=len(top)) as pool:
            for src, text in zip(top, pool.map(lambda s: fetch_page_text(s.source_url), top)):
                src.page_text = text


search_engine = SearchEngine()
