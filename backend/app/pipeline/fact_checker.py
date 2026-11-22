import time
from datetime import datetime
import logging
from typing import List

from ..config import settings
from ..models.schemas import FactCheckRequest, FactCheckResponse, ClaimAnalysis, VerdictEnum
from ..utils.text_utils import detect_language, extract_search_keywords, clean_text
from .claim_extractor import claim_extractor
from .search_engine import search_engine
from .gemini_analyzer import gemini_analyzer
from .reliability_scorer import reliability_scorer

logger = logging.getLogger("fact_checker.pipeline")

class FactCheckingPipeline:
    """Full Fact-Checking Pipeline Orchestrator."""

    def process(self, request: FactCheckRequest) -> FactCheckResponse:
        start_time = time.time()
        raw_text = clean_text(request.text)

        # 1. Language detection
        lang = request.language if request.language and request.language != "auto" else detect_language(raw_text)

        # 2. Claim extraction
        extracted_claims = claim_extractor.extract_claims(raw_text, lang)
        if not extracted_claims:
            extracted_claims = [raw_text]

        analyzed_claims: List[ClaimAnalysis] = []

        # 3. Analyse each claim
        for idx, claim_text in enumerate(extracted_claims):
            clean_claim, search_query = extract_search_keywords(claim_text, lang)

            # Web search: avval da'voning o'zi (mavzu bo'yicha manbalar), keyin fact-check so'rovi
            sources, fact_checks = search_engine.search_evidence(clean_claim, claim_text=claim_text, lang=lang)
            fc_sources, fc_extra = search_engine.search_evidence(search_query, claim_text=claim_text, use_wikipedia=False, lang=lang)
            existing_urls = {s.source_url for s in sources}
            for es in fc_sources:
                if es.source_url not in existing_urls:
                    sources.append(es)
                    existing_urls.add(es.source_url)
            known_fc = {f.url for f in fact_checks}
            fact_checks.extend(f for f in fc_extra if f.url not in known_fc)

            # Eng ishonchli manbalar bo'yicha ishonchlilik tartibida saralab, sahifa matnini olamiz.
            # Tartib shu yerda qat'iylashadi: Overview'dagi [1], [2] raqamlari shu ro'yxatga tayanadi.
            sources.sort(key=lambda s: s.source_reliability, reverse=True)
            sources = sources[:settings.MAX_SEARCH_RESULTS_PER_CLAIM]
            search_engine.enrich_with_page_text(sources)

            # Gemini analysis
            analysis_dict = gemini_analyzer.analyze_claim_evidence(
                claim=claim_text,
                sources=sources,
                language=lang,
            )

            verdict: VerdictEnum = analysis_dict["verdict"]
            confidence: float = analysis_dict["confidence"]
            reason: str = analysis_dict["reason"]
            evidences = analysis_dict["evidence_items"]
            contradictions = analysis_dict["contradictions"]
            overview = analysis_dict.get("overview")

            # Reliability score
            rel_score, breakdown = reliability_scorer.calculate_score(
                verdict=verdict,
                sources=sources,
                evidences=evidences,
                contradictions=contradictions,
                previous_fact_checks=fact_checks,
                model_confidence=confidence,
            )

            analyzed_claim = ClaimAnalysis(
                claim_id=idx + 1,
                claim_text=claim_text,
                verdict=verdict,
                confidence=confidence,
                reliability_score=rel_score,
                score_grade=breakdown.score_grade,
                ai_explanation=reason,
                evidences=evidences,
                contradictions=contradictions,
                sources=sources,
                previous_fact_checks=fact_checks,
                scoring_breakdown=breakdown,
                overview=overview,
            )
            analyzed_claims.append(analyzed_claim)

        overall_verdict, overall_score, overall_grade, summary = self._aggregate_results(analyzed_claims, lang)

        elapsed = round(time.time() - start_time, 2)

        return FactCheckResponse(
            success=True,
            input_text=raw_text,
            overall_verdict=overall_verdict,
            overall_reliability_score=overall_score,
            overall_score_grade=overall_grade,
            claims_count=len(analyzed_claims),
            claims=analyzed_claims,
            summary=summary,
            execution_time_seconds=elapsed,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    def _aggregate_results(self, claims: List[ClaimAnalysis], lang: str):
        if not claims:
            return VerdictEnum.UNVERIFIED, 25.0, "Juda ishonchsiz", "Tahlil qilinadigan fakt topilmadi."

        verdicts = [c.verdict for c in claims]
        avg_score = round(sum(c.reliability_score for c in claims) / len(claims), 1)
        grade = reliability_scorer.get_score_grade(avg_score)

        if VerdictEnum.FALSE in verdicts:
            overall_verdict = VerdictEnum.FALSE
            summary = (
                f"Matndagi {len(claims)} ta da'vodan kamida bittasi rad etildi yoki yolg'on deb topildi."
                if lang == "uz"
                else f"At least one claim was debunked as FALSE."
            )
        elif VerdictEnum.MISLEADING in verdicts:
            overall_verdict = VerdictEnum.MISLEADING
            summary = (
                "Xabarda qisman haqiqat bor, lekin chalg'ituvchi kontekst yoki mubolag'a mavjud."
                if lang == "uz"
                else "Claim contains misleading details or lacking context."
            )
        elif all(v == VerdictEnum.TRUE for v in verdicts):
            overall_verdict = VerdictEnum.TRUE
            summary = (
                "Barcha da'volar ishonchli dalillar va manbalar orqali to'liq tasdiqlandi."
                if lang == "uz"
                else "All claims are verified as TRUE with reliable evidence."
            )
        else:
            overall_verdict = VerdictEnum.UNVERIFIED
            summary = (
                "Ushbu ma'lumotni to'liq tekshirish uchun internetda yetarli rasmiy dalillar topilmadi."
                if lang == "uz"
                else "Insufficient evidence found to verify this statement."
            )

        return overall_verdict, avg_score, grade, summary

# Compatibility wrapper for legacy code
class FactChecker:
    """Facade exposing a simple ``check_fact`` method expected by legacy tests."""
    def __init__(self):
        self._pipeline = FactCheckingPipeline()

    def check_fact(self, data):
        """Accept a dict or FactCheckRequest and return a FactCheckResponse."""
        if isinstance(data, dict):
            request = FactCheckRequest(**data)
        else:
            request = data
        return self._pipeline.process(request)

# Instance used by FastAPI routes and current tests
fact_checker_pipeline = FactCheckingPipeline()
