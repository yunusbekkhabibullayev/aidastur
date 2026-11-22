from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    TRUE = "TRUE"
    FALSE = "FALSE"
    MISLEADING = "MISLEADING"
    UNVERIFIED = "UNVERIFIED"


class SourceTypeEnum(str, Enum):
    OFFICIAL_GOVERNMENT = "OFFICIAL_GOVERNMENT"
    ACADEMIC_RESEARCH = "ACADEMIC_RESEARCH"
    MAJOR_NEWS = "MAJOR_NEWS"
    FACT_CHECK_ORG = "FACT_CHECK_ORG"
    REPUTABLE_REFERENCE = "REPUTABLE_REFERENCE"
    GENERAL_WEB = "GENERAL_WEB"
    LOW_RELIABILITY = "LOW_RELIABILITY"


class EvidenceRelationEnum(str, Enum):
    SUPPORTS = "SUPPORTS"
    REFUTES = "REFUTES"
    MISLEADING_CONTEXT = "MISLEADING_CONTEXT"
    INSUFFICIENT = "INSUFFICIENT"


class Source(BaseModel):
    source_title: str
    source_url: str
    source_domain: str
    source_date: Optional[str] = None
    source_excerpt: str
    source_type: SourceTypeEnum = SourceTypeEnum.GENERAL_WEB
    source_reliability: float = Field(default=0.5, ge=0.0, le=1.0)
    credibility_label: str = "Medium"
    # Sahifadan olingan matn: faqat Gemini uchun, API javobiga chiqmaydi
    page_text: Optional[str] = Field(default=None, exclude=True)
    image_url: Optional[str] = None  # Vikipediya maqolasi rasmi (karta uchun)


class PreviousFactCheck(BaseModel):
    claim: str
    fact_checker: str
    verdict: str
    date: Optional[str] = None
    url: str


class EvidenceItem(BaseModel):
    statement: str
    relation: EvidenceRelationEnum
    source_title: str
    source_url: str
    source_excerpt: Optional[str] = None


class ScoringBreakdown(BaseModel):
    evidence_quality_score: float = Field(..., description="Weight of source reputation & excerpts")
    source_diversity_score: float = Field(..., description="Score based on distinct corroborating domains")
    claim_alignment_score: float = Field(..., description="Semantic alignment between claim and findings")
    contradiction_penalty: float = Field(..., description="Deduction if conflicting reputable evidence exists")
    final_calculated_score: float = Field(..., description="Final bounded composite reliability score")
    score_grade: str = Field(..., description="Human-readable rating grade")


class OverviewSegment(BaseModel):
    """Javobning bir bo'lagi va unga asos bo'lgan manbalar (1-based, ClaimAnalysis.sources bo'yicha)."""
    text: str
    source_ids: List[int] = []


class Overview(BaseModel):
    """Google AI Overview uslubidagi qisqa javob: har bir gap manbalarga bog'langan."""
    segments: List[OverviewSegment] = []
    conflict_note: Optional[OverviewSegment] = None  # manbalar o'rtasidagi nomuvofiqlik haqida
    generated_by: str = "gemini"  # "gemini" yoki "extractive"


class ClaimAnalysis(BaseModel):
    claim_id: int
    claim_text: str
    verdict: VerdictEnum
    confidence: float = Field(..., ge=0.0, le=100.0)
    reliability_score: float = Field(..., ge=0.0, le=100.0)
    score_grade: str
    ai_explanation: str
    evidences: List[EvidenceItem] = []
    contradictions: List[str] = []
    sources: List[Source] = []
    previous_fact_checks: List[PreviousFactCheck] = []
    scoring_breakdown: Optional[ScoringBreakdown] = None
    overview: Optional[Overview] = None


class FactCheckRequest(BaseModel):
    text: str = Field(..., min_length=3, max_length=5000, description="Matn, fakt, maqola yoki xabar")
    language: Optional[str] = Field(default="auto", description="Til: uz, ru, en yoki auto")


class FactCheckResponse(BaseModel):
    success: bool
    input_text: str
    overall_verdict: VerdictEnum
    overall_reliability_score: float
    overall_score_grade: str
    claims_count: int
    claims: List[ClaimAnalysis]
    summary: str
    execution_time_seconds: float
    timestamp: str
    error: Optional[str] = None



class OverviewBullet(BaseModel):
    """Punkt: qisqa sarlavha + ma'lumot (masalan, "Maydoni: 21,2 ming km²") va manbalari."""
    label: str
    text: str
    source_ids: List[int] = []


class OverviewResponse(BaseModel):
    """Google AI Overview uslubidagi javob: hukm va ball yo'q, faqat manbali javob."""
    success: bool
    query: str
    language: str
    intro: List[OverviewSegment] = []
    bullets: List[OverviewBullet] = []
    sources: List[Source] = []
    generated_by: str = "gemini"  # "gemini" yoki "extractive"
    message: Optional[str] = None
    execution_time_seconds: float
    timestamp: str
