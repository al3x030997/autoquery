"""Tests for autoquery.extractor.note_parser."""
from pathlib import Path

from autoquery.extractor.note_parser import parse

FIXTURE = Path(__file__).parent / "fixtures" / "note_taker_sample.txt"


def test_parse_identity():
    result = parse(FIXTURE.read_text())
    ident = result["identity"]
    assert ident["name"] == "Aashna Avachat"
    assert ident["organization"] == "Neighborhood Literary Agency"
    assert ident["role"] == "Literary Agent"
    assert ident["email"] == "aashna@neighborhoodlit.com"
    assert ident["submission_portal"] == "QueryTracker"
    assert ident["availability"] == "OPEN"


def test_parse_global_conditions():
    result = parse(FIXTURE.read_text())
    gc = result["global_conditions"]
    assert any(c["strength"] == "REQUIRED" and "of color" in c["text"].lower() for c in gc)
    assert any(c["strength"] == "STRONGLY_PREFERRED" for c in gc)
    assert any(c["strength"] == "PREFERRED" for c in gc)


def test_parse_preference_sections():
    result = parse(FIXTURE.read_text())
    sections = result["preference_sections"]
    labels = [s["label"] for s in sections]
    assert labels == ["Picture Books", "Young Adult", "Adult"]

    pb = sections[0]
    assert pb["audience"] == ["picture_books"]
    assert "contemporary" in pb["genres"]
    assert any("Laugh-out-loud" in w for w in pb["wants"])
    assert any("Food-based" in d for d in pb["does_not_want"])

    ya = sections[1]
    assert "young_adult" in ya["audience"] and "new_adult" in ya["audience"]
    assert "forced proximity" in ya["tropes_wanted"]
    assert "instalove" in ya["tropes_excluded"]
    assert ya["comp_titles"][0]["title"].startswith("I'd Tell You I Love You")
    assert ya["comp_titles"][0]["author"] == "Ally Carter"


def test_parse_hard_nos():
    result = parse(FIXTURE.read_text())
    hn = result["hard_nos"]
    assert "sexual violence on the page" in hn["content"]
    assert "poetry collections" in hn["format"]
    assert "non-consensual romance" in hn["trope"]
    assert "children's non-fiction" in hn["category"]


def test_parse_submission():
    result = parse(FIXTURE.read_text())
    sub = result["submission"]
    cats = [b["category"] for b in sub if b.get("category")]
    assert "Picture Books" in cats
    assert "Young Adult" in cats


def test_parse_comps_and_taste():
    result = parse(FIXTURE.read_text())
    comps = result["comp_titles_high_priority"]
    assert any("Clique" in c["title"] for c in comps)
    taste = result["taste_references"]
    assert any("Pachinko" in b for b in taste["books"])
    assert "Yellowjackets" in taste["film_tv"]
    assert "Mitski" in taste["music"]


def test_parse_themes_and_flags():
    result = parse(FIXTURE.read_text())
    assert "found family" in result["cross_cutting_themes"]
    flags = result["confidence_flags"]
    assert any("country" in f.lower() for f in flags["inferred"])
    assert any("fantasy" in f.lower() for f in flags["nuanced"])
    assert any("response time" in f.lower() for f in flags["missing"])


def test_parse_empty():
    result = parse("")
    assert result["identity"]["name"] is None
    assert result["preference_sections"] == []
    assert result["hard_nos"] == {"content": [], "format": [], "trope": [], "category": []}


def test_parse_missing_optional_section():
    text = """STEP 1: IDENTITY
-----------------
Name: Solo Agent
Availability: CLOSED
"""
    result = parse(text)
    assert result["identity"]["name"] == "Solo Agent"
    assert result["identity"]["availability"] == "CLOSED"
    assert result["preference_sections"] == []
    assert result["global_conditions"] == []
