from typing import List, Dict, Any, Tuple
from ..models.schemas import Source, EvidenceItem, PreviousFactCheck, VerdictEnum, ScoringBreakdown


class ReliabilityScorer:
    """
    Evidence-based Reliability Scoring Engine:
    Sun'iy ravishda 100% deb belgilamasdan, real dalillar,
    manbalarning mustaqilligi va konsensusiga asoslangan holda
    matematik ball hisoblaydi.
    """

    @classmethod
    def get_score_grade(cls, score: float) -> str:
        if score <= 30.0:
            return "Juda ishonchsiz"
        elif score <= 50.0:
            return "Ishonchsiz"
        elif score <= 70.0:
            return "Noaniq"
        elif score <= 85.0:
            return "Ishonchli"
        else:
            return "Yuqori ishonchli"

    @classmethod
    def calculate_score(
        cls,
        verdict: VerdictEnum,
        sources: List[Source],
        evidences: List[EvidenceItem],
        contradictions: List[str],
        previous_fact_checks: List[PreviousFactCheck],
        model_confidence: float = 75.0
    ) -> Tuple[float, ScoringBreakdown]:
        """
        Grounded score hisoblash algoritmi.
        """
        # 1. Agar manbalar topilmagan bo'lsa
        if not sources or verdict == VerdictEnum.UNVERIFIED:
            evidence_quality = 15.0
            source_diversity = 10.0
            claim_alignment = 10.0
            contradiction_pen = 0.0
            final_score = 25.0
            return final_score, ScoringBreakdown(
                evidence_quality_score=round(evidence_quality, 1),
                source_diversity_score=round(source_diversity, 1),
                claim_alignment_score=round(claim_alignment, 1),
                contradiction_penalty=round(contradiction_pen, 1),
                final_calculated_score=round(final_score, 1),
                score_grade=cls.get_score_grade(final_score)
            )

        # 2. Evidence Quality (0 - 35 ball)
        # Manbalarning ishonchlilik o'rtachasi va snippet uzunligi
        avg_source_reliability = sum(s.source_reliability for s in sources) / len(sources)
        evidence_quality = min(35.0, avg_source_reliability * 35.0)

        # 3. Source Diversity (0 - 25 ball)
        # Turli xil mustaqil domenlar soni
        unique_domains = len(set(s.source_domain for s in sources if s.source_domain))
        diversity_factor = min(1.0, unique_domains / 3.0)  # 3+ mustaqil domen bo'lsa maksimal
        source_diversity = diversity_factor * 25.0

        # 4. Claim Alignment & Model Grounding (0 - 30 ball)
        # Modelning ishonchi (0-100) ni dalillar konsensusi bilan tortish
        valid_evidences = [e for e in evidences if e.relation in ["SUPPORTS", "REFUTES"]]
        alignment_ratio = len(valid_evidences) / max(1, len(evidences)) if evidences else 0.5
        claim_alignment = (min(100.0, max(0.0, model_confidence)) / 100.0 * 0.6 + alignment_ratio * 0.4) * 30.0

        # 5. Contradiction Penalty (0 - 20 ball chegirish)
        contradiction_pen = 0.0
        if contradictions:
            contradiction_pen = min(20.0, len(contradictions) * 8.0)

        # 6. Previous Fact-Check Bonus (agar tekshiruvchi tashkilot allaqachon tekshirgan bo'lsa)
        fc_bonus = 5.0 if previous_fact_checks else 0.0

        # Raw composite certainty of evaluation (0 - 100)
        assessment_certainty = (evidence_quality + source_diversity + claim_alignment + fc_bonus) - contradiction_pen
        assessment_certainty = max(10.0, min(95.0, assessment_certainty))

        # Yakuniy ball verdict xarakteriga ko'ra belgilanadi:
        if verdict == VerdictEnum.TRUE:
            # Fakt tasdiqlangan: ball yuqori ishonchlilik zonasi (71 - 95)
            final_score = max(72.0, min(95.0, assessment_certainty))
        elif verdict == VerdictEnum.FALSE:
            # Fakt rad etilgan: dalillar asosida qat'iy yolg'on deb topilgan
            # Agar assessment certainty yuqori bo'lsa, xulosaning aniqligi 85-95%
            final_score = max(75.0, min(95.0, assessment_certainty))
        elif verdict == VerdictEnum.MISLEADING:
            # Chalg'ituvchi kontekst (51 - 70)
            final_score = max(52.0, min(70.0, assessment_certainty * 0.8))
        else: # UNVERIFIED
            # Dalil yetarli emas (20 - 45)
            final_score = max(20.0, min(45.0, assessment_certainty * 0.5))

        final_score = round(final_score, 1)

        breakdown = ScoringBreakdown(
            evidence_quality_score=round(evidence_quality, 1),
            source_diversity_score=round(source_diversity, 1),
            claim_alignment_score=round(claim_alignment, 1),
            contradiction_penalty=round(contradiction_pen, 1),
            final_calculated_score=final_score,
            score_grade=cls.get_score_grade(final_score)
        )

        return final_score, breakdown


reliability_scorer = ReliabilityScorer()

