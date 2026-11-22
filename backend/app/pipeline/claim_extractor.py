import re
import json
import logging
from typing import List
from ..config import settings
from ..utils.text_utils import clean_text

logger = logging.getLogger("fact_checker.claim_extractor")


class ClaimExtractor:
    """
    Foydalanuvchi kiritgan har qanday matndan (oddiy fakt, post, maqola)
    mustaqil va faktik tekshirilishi mumkin bo'lgan claim'larni ajratib oladi.
    """

    def extract_claims(self, text: str, lang: str = "uz") -> List[str]:
        cleaned = clean_text(text)
        if not cleaned:
            return []

        # Agar Gemini API mavjud bo'lsa, AI orqali ajratamiz
        if settings.GEMINI_API_KEY:
            ai_claims = self._extract_with_gemini(cleaned, lang)
            if ai_claims:
                return ai_claims[:settings.MAX_CLAIMS_PER_INPUT]

        # Aks holda aqlli qoida-asosidagi (rule-based) NLP segmentatsiyasi
        return self._extract_rule_based(cleaned)[:settings.MAX_CLAIMS_PER_INPUT]

    def _extract_with_gemini(self, text: str, lang: str) -> List[str]:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY)

            system_instruction = (
                "You are an expert NLP Fact-Checking Claim Extraction specialist. "
                "Given a user input text, extract distinct, atomic, verifiable factual claims. "
                "Ignore subjective opinions, greetings, emotional statements, or metaphors. "
                "Preserve the exact factual meaning. Return ONLY a valid JSON array of strings: "
                "[\"Claim 1\", \"Claim 2\"]. If there is only one claim, return [\"Claim 1\"]."
            )

            prompt = f"Text to extract verifiable claims from:\n\"\"\"{text}\"\"\"\nLanguage: {lang}\nOutput strictly JSON array:"

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.1,
                    response_mime_type="application/json"
                )
            )

            if response and response.text:
                result = json.loads(response.text.strip())
                if isinstance(result, list) and len(result) > 0:
                    return [str(c).strip() for c in result if str(c).strip()]
        except Exception as e:
            logger.warning(f"Gemini claim extraction failed: {e}. Falling back to rule-based segmentation.")

        return []

    def _extract_rule_based(self, text: str) -> List[str]:
        """
        Matndagi gaplar va punktuatsiyalarni tahlil qilib, da'volarni ajratadi.
        """
        # 1. Check for bullet points or numbered lists
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        bullet_claims = []
        for line in lines:
            line_clean = re.sub(r'^[\d\.\-\*\•\)\s]+', '', line).strip()
            if len(line_clean) > 10:
                bullet_claims.append(line_clean)

        if len(bullet_claims) > 1 and len(bullet_claims) == len(lines):
            return bullet_claims

        # 2. Split by sentence terminators (. ! ? ; and newlines)
        sentences = re.split(r'(?<=[.!?;\n])\s+', text)
        claims = []
        for s in sentences:
            s_clean = s.strip()
            # Olib tashlanadigan kirish so'zlar
            s_clean = re.sub(r'^(salom|assalomu alaykum|diqqat|muhim|xushxabar|shoshiling)[:\s]*', '', s_clean, flags=re.I).strip()
            if len(s_clean) >= 8:
                claims.append(s_clean)

        return claims if claims else [text.strip()]


claim_extractor = ClaimExtractor()

