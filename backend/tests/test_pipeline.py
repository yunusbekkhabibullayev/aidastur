import unittest
import sys
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.models.schemas import FactCheckRequest, VerdictEnum
from app.pipeline.fact_checker import fact_checker_pipeline
from app.pipeline.claim_extractor import claim_extractor
from app.pipeline.source_analyzer import SourceAnalyzer
from app.pipeline.reliability_scorer import reliability_scorer


class TestAIFactCheckerPipeline(unittest.TestCase):

    def test_01_true_fact(self):
        """Test 1: TRUE - Tasdiqlangan ilmiy fakt"""
        req = FactCheckRequest(text="Yer Quyosh atrofida aylanadi.", language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertEqual(res.overall_verdict, VerdictEnum.TRUE)
        self.assertGreaterEqual(res.overall_reliability_score, 70.0)
        self.assertGreater(len(res.claims[0].sources), 0)

    def test_02_false_fact(self):
        """Test 2: FALSE - Rad etilgan/soxta xabar"""
        req = FactCheckRequest(text="O'zbekistonda 2027-yildan barcha talabalar bepul iPhone oladi.", language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        # O'zbekistonda bepul iPhone tarqatilishi haqidagi da'vo UNVERIFIED yoki FALSE bo'lishi kerak
        self.assertIn(res.overall_verdict, [VerdictEnum.FALSE, VerdictEnum.UNVERIFIED])
        # Hech qachon asossiz TRUE bo'lmasligi kerak
        self.assertNotEqual(res.overall_verdict, VerdictEnum.TRUE)

    def test_03_misleading_fact(self):
        """Test 3: MISLEADING - Konteksti buzilgan fakt"""
        req = FactCheckRequest(text="Limon va iliq suv barcha saraton kasalliklarini butunlay yo'q qiladi.", language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertIn(res.overall_verdict, [VerdictEnum.FALSE, VerdictEnum.MISLEADING, VerdictEnum.UNVERIFIED])
        self.assertNotEqual(res.overall_verdict, VerdictEnum.TRUE)

    def test_04_unverified_fact(self):
        """Test 4: UNVERIFIED - Hech qanday ishonchli dalil mavjud bo'lmagan xabar"""
        req = FactCheckRequest(text="2049-yilda Mars sayyorasida yerliklarning birinchi yashirin yerosti qishlog'i qurib bitkazildi.", language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertEqual(res.overall_verdict, VerdictEnum.UNVERIFIED)
        self.assertLessEqual(res.overall_reliability_score, 50.0)

    def test_05_multiple_claims(self):
        """Test 5: Multiple Claims - Bitta matnda 2 ta alohida da'vo"""
        compound_text = "Yer Quyosh atrofida aylanadi. Toshkent O'zbekistonning poytaxti hisoblanadi."
        claims = claim_extractor.extract_claims(compound_text, lang="uz")
        self.assertGreaterEqual(len(claims), 2)

        req = FactCheckRequest(text=compound_text, language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.claims_count, 2)
        self.assertEqual(res.overall_verdict, VerdictEnum.TRUE)

    def test_06_uzbek_language(self):
        """Test 6: Uzbek Language - O'zbek tilida to'liq tekshirish"""
        req = FactCheckRequest(text="Toshkent — O'zbekiston Respublikasining poytaxti.", language="uz")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertEqual(res.overall_verdict, VerdictEnum.TRUE)
        self.assertGreater(len(res.claims[0].sources), 0)

    def test_07_russian_language(self):
        """Test 7: Russian Language - Rus tilida fakt tekshirish"""
        req = FactCheckRequest(text="Вода закипает при 100 градусах Цельсия при нормальном атмосферном давлении.", language="ru")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertEqual(res.overall_verdict, VerdictEnum.TRUE)

    def test_08_english_language(self):
        """Test 8: English Language - Ingliz tilida fakt tekshirish"""
        req = FactCheckRequest(text="The Moon orbits around the Earth.", language="en")
        res = fact_checker_pipeline.process(req)
        self.assertTrue(res.success)
        self.assertEqual(res.overall_verdict, VerdictEnum.TRUE)

    def test_source_credibility_logic(self):
        """Manba turlari va ishonchlilik koeffitsientini tekshirish"""
        gov_type, gov_score, _ = SourceAnalyzer.classify_source("https://lex.uz/docs/1234")
        self.assertEqual(gov_type.value, "OFFICIAL_GOVERNMENT")
        self.assertGreaterEqual(gov_score, 0.85)
        self.assertLess(gov_score, 1.0)  # Never 100%

        fake_type, fake_score, _ = SourceAnalyzer.classify_source("https://tiktok.com/@fake/video")
        self.assertEqual(fake_type.value, "LOW_RELIABILITY")
        self.assertLessEqual(fake_score, 0.40)


if __name__ == "__main__":
    unittest.main()
