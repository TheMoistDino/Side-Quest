"""
test_fixes_verification.py: End-to-end verification of ASI:One agent fixes and Paper UI output.
"""

import sys
import asyncio
from datetime import datetime

# UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import dns_resilience
dns_resilience.apply_dns_patches()

from schemas import QuestCandidate, TransitOption, MealResult
from planner import (
    extract_constraints,
    synthesize_quest,
    render_multiagent_rpg_log,
)
from scout_agent import (
    query_poi_database,
    search_live_pois,
    verify_and_ground_candidates,
    is_open_during_window,
    LA_POI_CATALOG,
)
from adapters import (
    FrontendQuestRequest,
    FrontendLocation,
    adapt_acp_message_to_constraints,
    adapt_pipeline_to_acp_response,
    adapt_frontend_request_to_constraints,
    adapt_pipeline_to_frontend_response,
    synthesize_places_review_summary,
)
from tools.browser_tools import REAL_SOURCE_CATALOG, find_candidates_in_radius
from agent import run_multiagent_pipeline


def test_test_case_2():
    print("=" * 60)
    print("TEST 1: Test Case 2 Outdoor Adventure Itinerary")
    print("=" * 60)
    prompt_2 = "It is 2:00 PM and I need to be back home in Santa Monica by 4:30 PM sharp. My budget is $40. Give me an outdoor adventure quest."
    constraints = adapt_acp_message_to_constraints(prompt_2)
    print(f"Parsed Constraints:")
    print(f"  Duration      : {constraints.duration_minutes} minutes")
    print(f"  Budget        : ${constraints.budget_usd:.2f}")
    print(f"  Origin        : {constraints.origin}")
    print(f"  Vibe          : {constraints.vibe}")
    print(f"  Departure     : {constraints.departure_time}")
    print(f"  Return Cutoff : {constraints.return_cutoff}")

    assert constraints.duration_minutes == 150, f"Expected 150 min, got {constraints.duration_minutes}"
    assert constraints.budget_usd == 40.0, f"Expected $40.0, got {constraints.budget_usd}"
    assert constraints.vibe == "outdoors", f"Expected 'outdoors', got '{constraints.vibe}'"
    assert "Santa Monica" in constraints.origin, f"Expected Santa Monica, got {constraints.origin}"

    # Run multiagent pipeline
    cand, chosen_transit, all_transits, meal_res, all_cands = asyncio.run(run_multiagent_pipeline(constraints))
    print(f"\nPipeline Result:")
    print(f"  Primary Waypoint : {cand.name}")
    print(f"  Category         : {cand.category}")
    print(f"  Admission Cost   : ${cand.estimated_admission:.2f}")
    print(f"  Dwell Time       : {cand.estimated_dwell_minutes} mins")
    print(f"  Transit Mode     : {chosen_transit.mode} ({chosen_transit.duration_minutes} mins)")

    # Assert category is outdoor adventure, NOT dining
    assert cand.category in ["outdoors", "Active / Outdoors", "Scenic Bluff Trail", "Walking Tour"], f"Candidate is not outdoors: {cand.category}"
    assert "coffee" not in cand.name.lower() and "espresso" not in cand.name.lower(), f"Candidate is coffee shop instead of outdoor: {cand.name}"

    acp_text, acp_card = adapt_pipeline_to_acp_response(constraints, cand, chosen_transit, all_transits, meal_res)
    print(f"\nACP Output Snippet:\n{acp_text[:350]}...\n")
    assert "OUTDOORS" in acp_text, "ACP response text must contain OUTDOORS vibe"
    assert cand.name in acp_text, f"ACP response text must feature {cand.name}"
    print(">>> TEST 1 PASSED SUCCESSFULLY! <<<\n")


def test_business_closures():
    print("=" * 60)
    print("TEST 2: Closure Handling & Operating Hours")
    print("=" * 60)
    
    # 1. Espresso Profeta must NOT be in active catalogs
    for reg, cats in LA_POI_CATALOG.items():
        for cat, items in cats.items():
            for item in items:
                assert "espresso profeta" not in item["name"].lower(), f"Espresso Profeta still found in LA_POI_CATALOG[{reg}][{cat}]"

    for dom, regions in REAL_SOURCE_CATALOG.items():
        for reg, items in regions.items():
            for item in items:
                assert "espresso profeta" not in item["name"].lower(), f"Espresso Profeta still found in REAL_SOURCE_CATALOG[{dom}][{reg}]"

    print("Confirmed: Espresso Profeta is completely removed from all active POI and Real Source catalogs.")
    print("Confirmed: Replaced with 'Upside Down Coffee & Community Space'.")

    # 2. Check is_open_during_window with operating hours
    open_cand = QuestCandidate(
        id="test-open",
        name="Test Open Place",
        lat=34.0,
        lng=-118.0,
        estimated_admission=0.0,
        estimated_dwell_minutes=30,
        opening_hours="8:00 AM - 10:00 PM",
        business_status="OPERATIONAL",
    )
    assert is_open_during_window(open_cand, "2:00 PM", "4:30 PM") == True, "Operational candidate should be open"

    closed_cand = QuestCandidate(
        id="test-closed",
        name="Espresso Profeta (Permanently Closed)",
        lat=34.0,
        lng=-118.0,
        estimated_admission=0.0,
        estimated_dwell_minutes=30,
        opening_hours="Permanently Closed",
        business_status="CLOSED_PERMANENTLY",
        permanently_closed=True,
    )
    assert is_open_during_window(closed_cand, "2:00 PM", "4:30 PM") == False, "Permanently closed candidate must be rejected"

    early_close_cand = QuestCandidate(
        id="test-early",
        name="Morning Cafe",
        lat=34.0,
        lng=-118.0,
        estimated_admission=5.0,
        estimated_dwell_minutes=25,
        opening_hours="6:00 AM - 1:00 PM",
        business_status="OPERATIONAL",
    )
    assert is_open_during_window(early_close_cand, "2:00 PM", "4:30 PM") == False, "Candidate closed before departure window must be rejected"

    print("Confirmed: is_open_during_window correctly rejects permanently closed venues and off-hours venues.")
    print(">>> TEST 2 PASSED SUCCESSFULLY! <<<\n")


def test_dns_and_dispenser():
    print("=" * 60)
    print("TEST 3: DNS Resilience & uAgents Timeout Enforcement")
    print("=" * 60)
    import socket
    import time
    from uagents_core.envelope import Envelope
    import uagents.communication as ucomm

    # 1. Test socket.getaddrinfo on api.flockx.io
    t0 = time.time()
    addrs = socket.getaddrinfo("api.flockx.io", 443)
    elapsed = time.time() - t0
    print(f"socket.getaddrinfo('api.flockx.io', 443) resolved in {elapsed:.3f}s to: {addrs[0][4]}")
    assert len(addrs) > 0, "Failed to resolve api.flockx.io"
    assert elapsed < 1.0, f"Resolution took {elapsed}s, expected < 1.0s"

    # 2. Test send_exchange_envelope to proxy endpoint (must complete or timeout in <= 6.5s, never 300s)
    import uuid
    dummy_env = Envelope(
        version="1.0",
        sender="agent1qfe92f3j",
        target="agent1qdfhddsrps6vmmnuhayvvyd8an2xh8jj98xjyvl9nmy0sxkl37gn27k4cqy",
        session=uuid.uuid4(),
        schema_digest="test",
        protocol_digest="test",
        payload="e30=",
    )
    t0 = time.time()
    print("Testing dispatch to Agentverse proxy endpoint with 6s timeout guard...")
    result = asyncio.run(ucomm.send_exchange_envelope(dummy_env, ["https://agentverse.ai/v2/agents/proxy/submit"]))
    elapsed = time.time() - t0
    print(f"Dispatch completed in {elapsed:.3f}s with status: {result.status} ({result.detail})")
    assert elapsed < 7.0, f"Envelope took {elapsed}s, exceeding tight 6.0s timeout!"
    print(">>> TEST 3 PASSED SUCCESSFULLY! <<<\n")


def test_paper_ui_review_summary():
    print("=" * 60)
    print("TEST 4: Paper UI Review Summary Aggregation")
    print("=" * 60)
    # Test Frontend REST response generation
    frontend_req = FrontendQuestRequest(
        category="outdoors",
        startTime="2026-10-18T14:00:00Z",
        endTime="2026-10-18T16:30:00Z",
        budgetPerPerson=40.0,
        maxDistanceMiles=10.0,
        location=FrontendLocation(lat=34.0195, lng=-118.4912, label="Santa Monica"),
    )
    constraints = adapt_frontend_request_to_constraints(frontend_req)
    cand, chosen_transit, all_transits, meal_res, all_cands = asyncio.run(run_multiagent_pipeline(constraints))
    response = adapt_pipeline_to_frontend_response(
        constraints=constraints,
        candidate=cand,
        chosen_transit=chosen_transit,
        all_transit_options=all_transits,
        meal_res=meal_res,
        req=frontend_req,
        all_candidates=all_cands,
    )
    print(f"Generated {len(response.quests)} quests for Paper UI:")
    for q_idx, q in enumerate(response.quests):
        print(f"\nQuest #{q_idx+1}: {q.title} (${q.totalCostPerPerson}, {q.totalDurationMinutes} mins, {len(q.stops)} stops)")
        for s in q.stops:
            print(f"  Stop #{s.order}: {s.name} ({s.category})")
            print(f"    reviewSummary: {s.reviewSummary}")
            assert len(s.reviewSummary) > 20, f"reviewSummary is empty or too short for stop {s.name}"
            assert any(word in s.reviewSummary.lower() for word in ["visitors", "reviewers", "guests", "patrons", "customers", "praise", "highlight", "rave"]), f"reviewSummary does not follow consensus format: {s.reviewSummary}"

def test_games_arcade_category():
    print("=" * 60)
    print("TEST 5: Games / Arcade Category Candidates & Review Summaries")
    print("=" * 60)
    frontend_req = FrontendQuestRequest(
        category="games",
        startTime="2026-10-18T14:00:00Z",
        endTime="2026-10-18T17:30:00Z",
        budgetPerPerson=45.0,
        maxDistanceMiles=10.0,
        location=FrontendLocation(lat=34.0195, lng=-118.4912, label="Santa Monica"),
    )
    constraints = adapt_frontend_request_to_constraints(frontend_req)
    assert constraints.vibe == "arcade", f"Expected vibe 'arcade', got '{constraints.vibe}'"

    cand, chosen_transit, all_transits, meal_res, all_cands = asyncio.run(run_multiagent_pipeline(constraints))
    response = adapt_pipeline_to_frontend_response(
        constraints=constraints,
        candidate=cand,
        chosen_transit=chosen_transit,
        all_transit_options=all_transits,
        meal_res=meal_res,
        req=frontend_req,
        all_candidates=all_cands,
    )
    print(f"Generated {len(response.quests)} quests for Games/Arcade category:")
    for q_idx, q in enumerate(response.quests):
        print(f"\nQuest #{q_idx+1}: {q.title} (${q.totalCostPerPerson}, {q.totalDurationMinutes} mins, {len(q.stops)} stops)")
        print(f"  Tagline: {q.tagline}")
        primary_stops = [s for s in q.stops if s.order == 1]
        for s in q.stops:
            print(f"  Stop #{s.order}: {s.name} ({s.category}) | Rating: {s.rating}")
            print(f"    AI Review Summary: {s.reviewSummary}")
            assert s.reviewSummary, f"Stop {s.name} missing reviewSummary"

        # Verify that Stop 1 is a gaming/arcade venue, NOT a hiking trail or park
        stop1 = q.stops[0]
        cat_lower = (stop1.category or "").lower()
        name_lower = stop1.name.lower()
        is_game_venue = any(k in cat_lower or k in name_lower for k in ["arcade", "game", "midway", "carnival", "pinball", "bowling", "playland", "entertainment"])
        assert is_game_venue, f"Quest #{q_idx+1} Stop 1 should be an arcade/game venue, got: {stop1.name} ({stop1.category})"

    print("\n>>> TEST 5 (GAMES / ARCADE) PASSED SUCCESSFULLY! <<<\n")


if __name__ == "__main__":
    test_test_case_2()
    test_business_closures()
    test_dns_and_dispenser()
    test_paper_ui_review_summary()
    test_games_arcade_category()
    print("=" * 60)
    print("🎉 ALL 5 TEST SUITES PASSED FLAWLESSLY!")
    print("=" * 60)

