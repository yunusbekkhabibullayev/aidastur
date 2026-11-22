import os
import pytest
from backend.app.pipeline.source_analyzer import SourceAnalyzer
from backend.app.models.schemas import SourceTypeEnum

# Helper to classify and return type & score
def classify(url, title="", excerpt=""):
    return SourceAnalyzer.classify_source(url, title=title, excerpt=excerpt)

@pytest.mark.parametrize("domain,expected_type", [
    ("lex.uz", SourceTypeEnum.OFFICIAL_GOVERNMENT),
    ("gov.uz", SourceTypeEnum.OFFICIAL_GOVERNMENT),
    ("stat.uz", SourceTypeEnum.OFFICIAL_GOVERNMENT),
])
def test_primary_sources(domain, expected_type):
    url = f"https://{domain}/some/path"
    src_type, score, label = classify(url, title="Sample Title", excerpt="Some excerpt text that is long enough to be considered informative.")
    assert src_type == expected_type, f"{domain} classified as {src_type}, expected {expected_type}"
    assert 0.10 <= score <= 0.95

@pytest.mark.parametrize("domain,expected_type", [
    ("kun.uz", SourceTypeEnum.MAJOR_NEWS),
    ("daryo.uz", SourceTypeEnum.MAJOR_NEWS),
    ("gazeta.uz", SourceTypeEnum.MAJOR_NEWS),
    ("qalampir.uz", SourceTypeEnum.MAJOR_NEWS),
    ("zamon.uz", SourceTypeEnum.MAJOR_NEWS),
])
def test_secondary_sources(domain, expected_type):
    url = f"https://{domain}/article/123"
    src_type, score, label = classify(url, title="News Title", excerpt="Detailed news article content that exceeds one hundred characters to trigger richness bonus.")
    assert src_type == expected_type, f"{domain} classified as {src_type}, expected {expected_type}"
    assert 0.10 <= score <= 0.95

def test_unknown_domain_not_trusted():
    url = "https://unknownsite.example.com/story"
    src_type, score, label = classify(url, title="Random Title", excerpt="Short.")
    assert src_type == SourceTypeEnum.GENERAL_WEB
    # Score should be the default baseline after adjustments, still within bounds
    assert 0.10 <= score <= 0.95

@pytest.mark.parametrize("url,expected_domain", [
    ("http://www.lex.uz", "lex.uz"),
    ("https://lex.uz/document/123", "lex.uz"),
    ("https://fakelex.uz", "fakelex.uz"),
    ("https://lex.uz.fake.com", "lex.uz.fake.com"),
])
def test_domain_parsing(url, expected_domain):
    domain = SourceAnalyzer.extract_domain(url)
    assert domain == expected_domain

def test_environment_overrides(monkeypatch):
    # Override primary and secondary sets via env vars
    monkeypatch.setenv("PRIMARY_SOURCES", "customprimary.uz")
    monkeypatch.setenv("SECONDARY_SOURCES", "customsecondary.uz")
    # Re‑initialize class attributes by re‑executing the module import logic
    import importlib
    import backend.app.pipeline.source_analyzer as sa_mod
    importlib.reload(sa_mod)
    # Now test that custom domains are recognized
    src_type, score, _ = sa_mod.SourceAnalyzer.classify_source("https://customprimary.uz/page")
    assert src_type == SourceTypeEnum.OFFICIAL_GOVERNMENT
    src_type2, score2, _ = sa_mod.SourceAnalyzer.classify_source("https://customsecondary.uz/story")
    assert src_type2 == SourceTypeEnum.MAJOR_NEWS

def test_duplicate_syndicated_detection():
    title = "Important Policy Announcement"
    url1 = "https://gov.uz/announcement"
    url2 = "https://kun.uz/announcement"
    # First classification – no penalty
    _, score1, _ = classify(url1, title=title, excerpt="Long excerpt content that is definitely more than one hundred characters to trigger the richness boost.")
    # Second classification – same title on different domain should incur penalty
    _, score2, _ = classify(url2, title=title, excerpt="Long excerpt content that is definitely more than one hundred characters to trigger the richness boost.")
    assert score2 < score1, "Syndicated duplicate should lower the reliability score"
    # Ensure both scores stay within bounds
    assert 0.10 <= score1 <= 0.95
    assert 0.10 <= score2 <= 0.95

def test_pipeline_integration():
    # Simple end‑to‑end fact‑check call to ensure pipeline still runs
    from backend.app.pipeline.fact_checker import FactChecker
    fc = FactChecker()
    response = fc.check_fact({"text": "The capital of Uzbekistan is Tashkent."})
    # Should return a FactCheckResponse with success=True and overall verdict present
    assert response.success is True
    assert response.overall_verdict in ["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]

