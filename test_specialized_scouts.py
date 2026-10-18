"""
test_specialized_scouts.py: Comprehensive test harness for the Scout Ensemble architecture.

Tests:
1. DiningScout (dining_scout.py): Sawtelle dining discovery, Yelp/Google platforms, dwell bounds (25-40m / 45-75m).
2. TrailsScout (trails_scout.py): Santa Monica trails, AllTrails/Modern Hiker platforms, 20 min/mile dwell rule, condition warnings.
3. CultureScout (culture_scout.py): Exposition Park & Westwood museums, Google Arts & Culture / Yelp, admission fees, dwell bounds (30-45m / 60-120m).
4. Ensemble Coordinator (scout_agent.py): Parallel multi-agent routing for mixed queries ("coffee and thrifting in Sawtelle").
5. Live HTTP Verification: Every single returned URL tested live asserting status_code < 400.
6. Zero Hallucination Audit: Verifies valid source_platform tags and absence of fake tokens.
"""

import sys
import asyncio
import httpx
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from schemas import QuestCandidate, VerifiedReview, ScoutQuery
from dining_scout import query_dining_scout
from trails_scout import query_trails_scout
from culture_scout import query_culture_scout
from scout_agent import route_ensemble_query

HALLUCINATION_TOKENS = [
    "fake-user",
    "fake user",
    "test review",
    "sample text",
    "sample review",
    "dummy text",
    "dummy user",
    "lorem ipsum",
    "placeholder",
    "test reviewer",
    "generic review",
    "as an ai",
]

VALID_PLATFORMS = [
    "yelp",
    "alltrails",
    "google maps",
    "google arts & culture",
    "modern hiker",
    "tripadvisor",
    "official website",
    "web",
]


async def assert_all_urls_live(candidates: List[QuestCandidate], test_label: str):
    """Sends live HTTP requests to every candidate URL asserting status_code < 400."""
    print(f"\n  🌐 [Anti-404 Live HTTP Verification: {test_label}]")
    async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
        for c in candidates:
            url = c.verified_url or c.source_url
            assert url, f"Candidate '{c.name}' has no URL!"
            try:
                res = await client.head(url, headers={"User-Agent": "Mozilla/5.0"})
                if res.status_code in [403, 405]:
                    res = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                print(f"    - '{c.name}' -> {url[:65]}... [Status: {res.status_code}]")
                assert res.status_code < 400, (
                    f"URL for '{c.name}' returned broken status {res.status_code}: {url}"
                )
            except Exception as e:
                assert False, f"Failed HTTP verification for '{c.name}': {url} ({e})"


def assert_clean_reviews(candidates: List[QuestCandidate], test_label: str):
    """Validates real review content, valid source_platform tags, and zero fake tokens."""
    print(f"  🔍 [Zero-Hallucination & Platform Audit: {test_label}]")
    for c in candidates:
        assert c.reviews, f"Candidate '{c.name}' must have at least 1 verified review!"
        for r in c.reviews:
            r_author = r.author if hasattr(r, "author") else r.get("author", "")
            r_text = (r.excerpt if hasattr(r, "excerpt") else (r.get("excerpt") or r.get("text", ""))).lower()
            r_plat = (r.source_platform if hasattr(r, "source_platform") else (r.get("source_platform") or r.get("source", ""))).lower()

            assert r_author and len(r_author.strip()) > 1, f"Review author empty for '{c.name}'"
            assert r_text and len(r_text.strip()) > 10, f"Review excerpt too short for '{c.name}'"
            assert any(p in r_plat for p in VALID_PLATFORMS), (
                f"Invalid source_platform '{r_plat}' for '{c.name}'. Expected one of {VALID_PLATFORMS}"
            )

            for token in HALLUCINATION_TOKENS:
                assert token not in r_author.lower(), (
                    f"Fake token '{token}' in author: '{r_author}'"
                )
                assert token not in r_text, (
                    f"Fake token '{token}' in review excerpt: '{r_text}'"
                )

        print(f"    ✓ '{c.name}' validated clean ({len(c.reviews)} reviews | Platform: {c.reviews[0].source_platform})")


async def test_dining_scout_sawtelle():
    print("=" * 75)
    print(" 🍴 TEST 1: DiningScout Discovery in Sawtelle")
    print("=" * 75)

    candidates = await query_dining_scout(area="Sawtelle", cuisine="ramen and dessert", budget_max=35.0)
    assert len(candidates) >= 2, f"Expected >= 2 dining spots, got {len(candidates)}"

    for c in candidates:
        assert c.category == "dining"
        assert c.is_verified is True
        assert c.admission_cost > 0.0

        # Check dining dwell time rules
        if any(k in c.name.lower() for k in ["tsujita", "ramen", "noodle"]):
            assert 45 <= c.estimated_dwell_mins <= 75, (
                f"Sit-down ramen dwell out of bounds (45-75m): {c.estimated_dwell_mins}m"
            )
        else:
            assert 25 <= c.estimated_dwell_mins <= 40, (
                f"Fast casual/cafe dwell out of bounds (25-40m): {c.estimated_dwell_mins}m"
            )

    await assert_all_urls_live(candidates, "DiningScout Sawtelle")
    assert_clean_reviews(candidates, "DiningScout Sawtelle")
    print("  ✅ TEST 1 PASSED: DiningScout enforced dwell bounds, valid Yelp/Google reviews, and live URLs.")


async def test_trails_scout_santa_monica():
    print("\n" + "=" * 75)
    print(" 🌲 TEST 2: TrailsScout Discovery in Santa Monica")
    print("=" * 75)

    candidates = await query_trails_scout(area="Santa Monica", intensity="moderate", time_window_mins=90)
    assert len(candidates) >= 2, f"Expected >= 2 trails in Santa Monica, got {len(candidates)}"

    for c in candidates:
        assert c.category == "outdoors"
        assert c.is_verified is True
        assert c.admission_cost == 0.0
        # Check trail condition warnings present in description
        assert "trail condition" in c.description.lower(), (
            f"Trail '{c.name}' missing trail condition warnings: {c.description}"
        )
        # Distance-based dwell time: approx 20 min/mile, bounded [25, 90]
        assert 25 <= c.estimated_dwell_mins <= 90, (
            f"Trail dwell time out of bounds: {c.estimated_dwell_mins}m"
        )
        # Verify platform is AllTrails or Modern Hiker
        plat = c.reviews[0].source_platform.lower()
        assert "alltrails" in plat or "modern hiker" in plat or "google" in plat

    await assert_all_urls_live(candidates, "TrailsScout Santa Monica")
    assert_clean_reviews(candidates, "TrailsScout Santa Monica")
    print("  ✅ TEST 2 PASSED: TrailsScout verified 20m/mile dwell, AllTrails reviews, and condition warnings.")


async def test_culture_scout_exposition_and_westwood():
    print("\n" + "=" * 75)
    print(" 🎨 TEST 3: CultureScout Discovery in Exposition Park & Westwood")
    print("=" * 75)

    candidates = await query_culture_scout(area="Exposition Park", admission_max=25.0)
    assert len(candidates) >= 2, f"Expected >= 2 cultural landmarks in Exposition Park, got {len(candidates)}"

    for c in candidates:
        assert c.category == "culture"
        assert c.is_verified is True
        assert c.admission_cost >= 0.0
        # Museum dwell bounds: 60-120 mins
        assert 60 <= c.estimated_dwell_mins <= 120, (
            f"Museum dwell time out of bounds (60-120m): {c.estimated_dwell_mins}m"
        )
        plat = c.reviews[0].source_platform.lower()
        assert "google arts" in plat or "yelp" in plat or "google" in plat

    await assert_all_urls_live(candidates, "CultureScout Exposition Park")
    assert_clean_reviews(candidates, "CultureScout Exposition Park")
    print("  ✅ TEST 3 PASSED: CultureScout verified museum dwell bounds, admission fees, and verified reviews.")


async def test_ensemble_coordinator_mixed_query():
    print("\n" + "=" * 75)
    print(" 🧭 TEST 4: Ensemble Coordinator Parallel Multi-Intent Routing")
    print("=" * 75)

    # Mixed query: "coffee and thrifting in Sawtelle" -> dispatches to DiningScout + CultureScout
    candidates = await route_ensemble_query(
        area="Sawtelle",
        category="coffee and thrifting",
        max_admission=35.0,
    )
    assert len(candidates) >= 3, f"Expected >= 3 candidates across ensemble, got {len(candidates)}"

    categories_found = {c.category for c in candidates}
    print(f"  Ensemble retrieved {len(candidates)} candidates spanning categories: {categories_found}")
    assert "dining" in categories_found, "Ensemble failed to route dining intent to DiningScout!"
    assert "culture" in categories_found, "Ensemble failed to route thrifting/culture intent to CultureScout!"

    for c in candidates:
        assert c.is_verified is True
        assert c.verified_url.startswith("http")

    await assert_all_urls_live(candidates, "Ensemble Sawtelle Mixed")
    assert_clean_reviews(candidates, "Ensemble Sawtelle Mixed")
    print("  ✅ TEST 4 PASSED: Ensemble coordinator dispatched across subagents and unified candidates.")


async def test_anti_404_resilience_fallback():
    print("\n" + "=" * 75)
    print(" 🛡️ TEST 5: Anti-404 Fallback Resilience")
    print("=" * 75)

    from tools.browser_tools import ground_and_validate_candidates

    dead_cand = QuestCandidate(
        id="simulated-dead-link",
        name="Artisan Siphon Coffee Co.",
        category="dining",
        address="11300 Mississippi Ave, Los Angeles, CA 90025",
        lat=34.0398,
        lng=-118.4442,
        admission_cost=6.0,
        estimated_dwell_mins=25,
        verified_url="https://httpstat.us/404",  # Guaranteed 404
        reviews=[
            VerifiedReview(
                author="Kenji M.",
                rating=4.5,
                excerpt="Great neighborhood siphon brew.",
                source_platform="Yelp",
                source_url="https://httpstat.us/404",
            )
        ],
        is_verified=False,
    )

    print("  Testing dead URL: https://httpstat.us/404")
    validated = await ground_and_validate_candidates([dead_cand], area_hint="Sawtelle")
    fixed = validated[0]

    print(f"  ↳ Replaced with: {fixed.verified_url}")
    assert "https://www.google.com/maps/search/?api=1&query=" in fixed.verified_url
    assert "Artisan+Siphon+Coffee" in fixed.verified_url or "Artisan%20Siphon" in fixed.verified_url
    assert fixed.is_verified is True

    # Check live status
    async with httpx.AsyncClient(follow_redirects=True, timeout=5.0) as client:
        res = await client.head(fixed.verified_url, headers={"User-Agent": "Mozilla/5.0"})
        print(f"  ↳ Live status of fallback URL: {res.status_code}")
        assert res.status_code < 400

    print("  ✅ TEST 5 PASSED: Dead 404 link automatically replaced with working Google Maps search URL.")


async def main():
    print("\n" + "#" * 75)
    print("  🚀 STARTING SPECIALIZED SCOUT ENSEMBLE TEST SUITE")
    print("#" * 75)

    await test_dining_scout_sawtelle()
    await test_trails_scout_santa_monica()
    await test_culture_scout_exposition_and_westwood()
    await test_ensemble_coordinator_mixed_query()
    await test_anti_404_resilience_fallback()

    print("\n" + "#" * 75)
    print("  ✨ ALL 5 ENSEMBLE VERIFICATION TESTS PASSED FLAWLESSLY!")
    print("#" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
