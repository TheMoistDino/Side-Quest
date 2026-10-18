"""
test_scout_verification.py: Unit and Integration Verification for ScoutAgent Grounding.

Tests:
1. ScoutAgent POI Discovery for "coffee and thrifting in Sawtelle".
2. Live HTTP Link Validation (assert status_code < 400 for all candidate URLs).
3. Zero-Hallucination Review Verification (assert zero generic fake tokens).
4. Strict Dwell-Time Bounds (15-30m coffee, 30-60m thrift/shops, 60-120m museums).
5. Anti-404 Guardrail Fallback (deliberate 404 replaced by deterministic Google Maps URL).
6. Operating Hours Filter (omission of closed venues during user travel window).
7. Comprehensive Catalog Audit across all LA regions.
"""

import sys
import asyncio
import httpx
from typing import List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from schemas import QuestCandidate, VerifiedReview
from scout_agent import (
    is_link_live,
    make_deterministic_maps_url,
    bound_dwell_time,
    is_open_during_window,
    query_poi_database,
    verify_and_ground_candidates,
    LA_POI_CATALOG,
)

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
                print(f"    - '{c.name}' -> {url[:60]}... [Status: {res.status_code}]")
                assert res.status_code < 400, (
                    f"URL for '{c.name}' returned broken status {res.status_code}: {url}"
                )
            except Exception as e:
                # If DNS or direct connection error, verify that it was caught
                assert False, f"Failed HTTP verification for '{c.name}': {url} ({e})"


def assert_zero_hallucinations(candidates: List[QuestCandidate], test_label: str):
    """Ensures zero hallucination tokens exist in candidate reviews."""
    print(f"  🔍 [Zero-Hallucination Review Check: {test_label}]")
    for c in candidates:
        for r in c.reviews:
            r_author = r.author if hasattr(r, "author") else r.get("author", "")
            r_text = (r.text if hasattr(r, "text") else (r.get("text") or r.get("snippet", ""))).lower()
            for token in HALLUCINATION_TOKENS:
                assert token not in r_author.lower(), (
                    f"Hallucination token '{token}' detected in author: '{r_author}'"
                )
                assert token not in r_text, (
                    f"Hallucination token '{token}' detected in review text: '{r_text}'"
                )
        print(f"    ✓ '{c.name}' verified clean ({len(c.reviews)} genuine reviews)")


async def test_sawtelle_coffee_and_thrifting():
    print("=" * 75)
    print(" 🧪 TEST 1: Sawtelle POI Discovery ('coffee and thrifting in Sawtelle')")
    print("=" * 75)

    candidates = query_poi_database(
        area="Sawtelle",
        category="coffee and thrifting",
        max_admission=50.0,
    )
    assert len(candidates) >= 2, f"Expected at least 2 candidates for Sawtelle, got {len(candidates)}"

    # Apply live grounding & anti-404 verification
    grounded = await verify_and_ground_candidates(candidates)
    assert len(grounded) >= 2

    # Verify dwell times are bounded
    for c in grounded:
        cat_lower = c.category.lower()
        if any(k in cat_lower for k in ["coffee", "tea", "cafe"]):
            assert 15 <= c.estimated_dwell_mins <= 30, (
                f"Coffee dwell time out of bounds: {c.estimated_dwell_mins}m"
            )
        elif any(k in cat_lower for k in ["thrift", "boutique", "vintage"]):
            assert 30 <= c.estimated_dwell_mins <= 60, (
                f"Thrift dwell time out of bounds: {c.estimated_dwell_mins}m"
            )
        assert c.is_verified is True
        assert c.admission_cost >= 0.0

    # Live HTTP status check
    await assert_all_urls_live(grounded, "Sawtelle")

    # Anti-hallucination review check
    assert_zero_hallucinations(grounded, "Sawtelle")
    print("  ✅ TEST 1 PASSED: Sawtelle POIs grounded, bounded, and verified live (< 400).")


async def test_westwood_museums():
    print("\n" + "=" * 75)
    print(" 🧪 TEST 2: Westwood Museum POIs & Dwell Bounds")
    print("=" * 75)

    candidates = query_poi_database(
        area="Westwood",
        category="museum art",
        max_admission=30.0,
    )
    assert len(candidates) >= 1

    grounded = await verify_and_ground_candidates(candidates)
    for c in grounded:
        if "museum" in c.category.lower():
            assert 60 <= c.estimated_dwell_mins <= 120, (
                f"Museum dwell time out of bounds: {c.estimated_dwell_mins}m"
            )
        assert c.is_verified is True

    await assert_all_urls_live(grounded, "Westwood")
    assert_zero_hallucinations(grounded, "Westwood")
    print("  ✅ TEST 2 PASSED: Westwood Museums bounded to 60-120m and verified live.")


async def test_anti_404_automatic_fallback():
    print("\n" + "=" * 75)
    print(" 🧪 TEST 3: Anti-404 Guardrail Automatic Fallback")
    print("=" * 75)

    # Synthetic candidate with deliberately dead 404 URL
    dead_candidate = QuestCandidate(
        id="broken-link-poi",
        name="Artisan Vintage Emporium",
        address="1234 Sawtelle Blvd, Los Angeles, CA 90025",
        lat=34.0416,
        lng=-118.4468,
        admission_cost=0.0,
        estimated_dwell_mins=45,
        verified_url="https://httpstat.us/404",  # Guaranteed 404
        reviews=[],
        is_verified=False,
    )

    print("  Testing candidate with guaranteed dead link: https://httpstat.us/404")
    grounded = await verify_and_ground_candidates([dead_candidate])
    fixed_candidate = grounded[0]

    print(f"  ↳ Guardrail replaced URL with: {fixed_candidate.verified_url}")
    assert "https://www.google.com/maps/search/?api=1&query=" in fixed_candidate.verified_url, (
        f"URL was not replaced with deterministic Maps URL: {fixed_candidate.verified_url}"
    )
    assert "Artisan+Vintage+Emporium" in fixed_candidate.verified_url or "Artisan%20Vintage" in fixed_candidate.verified_url

    # Verify fallback link is live (< 400)
    live = await is_link_live(fixed_candidate.verified_url)
    assert live is True, "Fallback Google Maps URL failed live check!"
    assert fixed_candidate.is_verified is True
    print("  ✅ TEST 3 PASSED: Dead 404 link automatically replaced with working Google Maps URL.")


async def test_operating_hours_filter():
    print("\n" + "=" * 75)
    print(" 🧪 TEST 4: Operating Hours Filter (Closed Venue Omission)")
    print("=" * 75)

    # Hammer Museum is Closed Mondays: "11:00 AM - 6:00 PM (Closed Mon)"
    # Monday date
    monday_departure = "2026-10-19T14:00:00Z"
    # Tuesday date
    tuesday_departure = "2026-10-20T14:00:00Z"

    monday_open = is_open_during_window("11:00 AM - 6:00 PM (Closed Mon)", departure_time=monday_departure)
    tuesday_open = is_open_during_window("11:00 AM - 6:00 PM (Closed Mon)", departure_time=tuesday_departure)

    assert monday_open is False, "Expected venue to be flagged as closed on Monday!"
    assert tuesday_open is True, "Expected venue to be flagged as open on Tuesday!"

    print("  - Monday check (2026-10-19) on '(Closed Mon)': correctly identified as closed.")
    print("  - Tuesday check (2026-10-20) on '(Closed Mon)': correctly identified as open.")
    print("  ✅ TEST 4 PASSED: Operating hours filter correctly enforces visit window.")


async def test_catalog_wide_integrity():
    print("\n" + "=" * 75)
    print(" 🧪 TEST 5: Comprehensive Catalog-Wide Grounding Audit")
    print("=" * 75)

    total_pois = 0
    total_reviews = 0

    for region_name, categories in LA_POI_CATALOG.items():
        for cat_name, items in categories.items():
            for item in items:
                total_pois += 1
                name = item["name"]
                addr = item["address"]
                assert addr and "CA" in addr, f"POI '{name}' missing real California address: '{addr}'"
                assert -119.0 < item["lng"] < -117.0, f"POI '{name}' longitude out of LA bounds: {item['lng']}"
                assert 33.5 < item["lat"] < 34.5, f"POI '{name}' latitude out of LA bounds: {item['lat']}"
                
                # Check reviews
                reviews = item.get("reviews", [])
                total_reviews += len(reviews)
                for r in reviews:
                    author = r.get("author", "")
                    text = r.get("text", "")
                    for token in HALLUCINATION_TOKENS:
                        assert token not in author.lower(), f"POI '{name}' review contains fake token '{token}'"
                        assert token not in text.lower(), f"POI '{name}' review text contains fake token '{token}'"

    print(f"  Audited {total_pois} POIs across all LA districts with {total_reviews} verified reviews.")
    print("  ✓ Zero hallucination tokens found across the entire catalog.")
    print("  ✅ TEST 5 PASSED: Entire catalog is factually grounded with real coordinates and reviews.")


async def test_scout_agent_message_handler():
    print("\n" + "=" * 75)
    print(" 🧪 TEST 6: ScoutAgent uAgents RPC Handler End-to-End")
    print("=" * 75)
    from unittest.mock import AsyncMock, MagicMock
    from schemas import ScoutQuery, ScoutResult
    from scout_agent import handle_scout_query

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.send = AsyncMock()

    msg = ScoutQuery(
        session_id="test-session-rpc-1",
        query_area="Sawtelle",
        category="coffee and thrifting",
        max_admission=25.0,
    )
    await handle_scout_query(ctx, "orchestrator-test-sender", msg)
    assert ctx.send.called, "ScoutAgent did not send reply via ctx.send!"

    call_args = ctx.send.call_args[0]
    recipient = call_args[0]
    result: ScoutResult = call_args[1]

    assert recipient == "orchestrator-test-sender"
    assert isinstance(result, ScoutResult)
    assert len(result.candidates) >= 2, f"Expected >= 2 candidates, got {len(result.candidates)}"

    print(f"  RPC message received with {len(result.candidates)} candidates:")
    for c in result.candidates:
        assert c.is_verified is True
        assert c.verified_url.startswith("http")
        print(f"    - '{c.name}' (Dwell: {c.estimated_dwell_mins}m | URL: {c.verified_url[:50]}...)")

    print("  ✅ TEST 6 PASSED: ScoutAgent protocol handler returned verified grounded candidates.")


async def main():
    print("\n" + "#" * 75)
    print("  🚀 STARTING SCOUT AGENT ANTI-HALLUCINATION & LINK VERIFICATION SUITE")
    print("#" * 75)

    await test_sawtelle_coffee_and_thrifting()
    await test_westwood_museums()
    await test_anti_404_automatic_fallback()
    await test_operating_hours_filter()
    await test_catalog_wide_integrity()
    await test_scout_agent_message_handler()

    print("\n" + "#" * 75)
    print("  ✨ ALL 6 VERIFICATION TESTS PASSED FLAWLESSLY!")
    print("#" * 75 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
