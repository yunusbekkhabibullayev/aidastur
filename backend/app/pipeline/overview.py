import time
import re
import logging
from datetime import datetime, timezone

from ..config import settings
from ..models.schemas import FactCheckRequest, OverviewResponse
from ..utils.text_utils import clean_text, detect_language
from .search_engine import search_engine, STOPWORDS, extract_core_subject_tokens, is_source_relevant, is_multi_claim_query
from .gemini_analyzer import gemini_analyzer

logger = logging.getLogger("fact_checker.overview")

OVERVIEW_MAX_SOURCES = 8


class OverviewPipeline:
    """Savol yoki da'vo -> manbalar -> Google AI Overview uslubidagi javob (hukmsiz)."""

    def process(self, request: FactCheckRequest) -> OverviewResponse:
        start = time.time()
        query = clean_text(request.text)
        lang = request.language if request.language and request.language != "auto" else detect_language(query)

        raw_sources, _ = search_engine.search_evidence(query, claim_text=query, lang=lang)

        # 0. Commercial/marketplace saytlarini har doim olib tashlaymiz (UI va AI uchun ham)
        from .source_analyzer import SourceAnalyzer as _SA
        raw_sources = [
            s for s in raw_sources
            if not _SA.is_commercial_or_marketplace(s.source_url, s.source_domain or "", s.source_title or "")
        ]

        # 1. Mavzuga moslik filtri (Relevance Filtering):
        # Multi-claim so'rovlarda (bir nechta gap) har bir gapning mavzusiga
        # mos kelgan manbalar qabul qilinadi.
        # Single-claim so'rovlarda faqat asosiy sub'ektga mos manbalar qoladi.
        multi_claim = is_multi_claim_query(query)
        sources = [s for s in raw_sources if is_source_relevant(query, s.source_title, s.source_excerpt, s.page_text or "")]

        # Agar filtr juda qattiq bo'lib, barcha manbalarni olib tashlagan bo'lsa —
        # multi-claim holida barcha manbalarni qaytarib beramiz (fallback)
        if not sources and raw_sources and multi_claim:
            sources = list(raw_sources)

        # 2. Relevance-aware sorting: so'rovdagi kalit so'zlar manbada qatnashishini hisobga olamiz
        q_tokens = [w.lower() for w in re.findall(r"[a-z\u0400-\u04ff']+", query) if len(w) >= 3 and w.lower() not in STOPWORDS]
        def source_score(s):
            target = (s.source_title + " " + s.source_excerpt).lower()
            matches = sum(1 for t in q_tokens if t in target)
            rel = (matches / len(q_tokens)) if q_tokens else 0.5
            # Agar Wikipediya maqolasida so'rov so'zlari umuman bo'lmasa, uni pastga suramiz
            if "wikipedia.org" in (s.source_domain or "") and rel == 0 and len(q_tokens) > 1:
                return -1.0
            return s.source_reliability + (rel * 0.8)

        sources.sort(key=source_score, reverse=True)
        sources = sources[:OVERVIEW_MAX_SOURCES]
        search_engine.enrich_with_page_text(sources)

        def finish(**kw):
            return OverviewResponse(
                success=True, query=query, language=lang, sources=sources,
                execution_time_seconds=round(time.time() - start, 2),
                timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), **kw,
            )

        # 4. Agar internetda da'vo bo'yicha hech qanday tasdiqlovchi manba topilmasa:
        if not sources:
            ai_ans = gemini_analyzer.generate_no_evidence_overview(query, lang)
            if ai_ans and (ai_ans.get("intro") or ai_ans.get("bullets")):
                return finish(
                    intro=ai_ans.get("intro", []),
                    bullets=ai_ans.get("bullets", []),
                    generated_by="gemini"
                )
            return finish(
                message="Ushbu so'rov yoki da'vo bo'yicha internetda va rasmiy manbalarda tasdiqlovchi ma'lumot topilmadi.",
                generated_by="none",
            )

        # 5. Manbalar tartibi shu yerda qat'iylashadi: javobdagi [1], [2] raqamlari shu ro'yxatga tayanadi
        answer = gemini_analyzer.generate_overview(query, sources, lang)
        generated_by = "gemini"
        if not answer:
            answer = gemini_analyzer.extractive_answer(sources)
            generated_by = "extractive"

        return finish(intro=answer["intro"], bullets=answer["bullets"], generated_by=generated_by)


overview_pipeline = OverviewPipeline()
