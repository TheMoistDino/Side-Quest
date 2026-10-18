"""
test_flow.py: Multi-Agent Pipeline Verification Harness.

Validates the full multi-agent loop:
1. User Constraints Extraction
2. ScoutAgent POI Discovery (ScoutQuery -> ScoutResult)
3. TransitAgent Multi-Modal Routing (TransitQuery -> TransitResult)
4. BudgetAgent Opportunistic Dining (MealQuery -> MealResult)
5. Multi-Agent RPG Sidequest Log Synthesis

Can run:
- In-memory mock/direct pipeline test: python test_flow.py
- Live ACP Bureau network test: python test_flow.py --live
"""

import os
import sys
import uuid
import asyncio
from datetime import datetime
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

from schemas import (
    ScoutQuery,
    ScoutResult,
    TransitQuery,
    TransitResult,
    MealQuery,
    MealResult,
)

from planner import (
    extract_constraints,
    render_multiagent_rpg_log,
)

from scout_agent import query_poi_database, search_live_pois
from transit_agent import calculate_multi_modal_options
from budget_agent import SIT_DOWN_OPTIONS, SNACK_OPTIONS

SAMPLE_TESTS = [
    (
        "Westwood Chill & Boba Adventure",
        "I have 2.5 hours and $35 starting from Westwood, looking for something chill and back by 6pm",
    ),
    (
        "Downtown LA Art & Food Odyssey",
        "3 hours free, $45 budget in Downtown LA for modern art and local food",
    ),
    (
        "Santa Monica Coastal Sprint",
        "90 minutes free, $15 budget near Santa Monica, need an outdoor recharge",
    ),
    (
        "Zero-Dollar Koreatown Cultural Recon",
        "Free for 1 hour in Koreatown, $0 budget, just exploring",
    ),
]


def run_pipeline_step_by_step(prompt: str):
    print("=" * 75)
    print(" 🎮 [TEST FLOW] Multi-Agent Pipeline Execution")
    print("=" * 75)
    print(f"Input Prompt: \"{prompt}\"")
    print("-" * 75)

    # Step 1: Constraint Extraction
    constraints = extract_constraints(prompt)
    session_id = str(uuid.uuid4())[:8]
    print(f"[Step 0: NLP Parsing]")
    print(f"  - Origin          : {constraints.origin}")
    print(f"  - Vibe / Category : {constraints.vibe}")
    print(f"  - Temporal Window : {constraints.duration_minutes} mins")
    print(f"  - Fiscal Budget   : ${constraints.budget_usd:.2f}")
    if constraints.return_cutoff:
        print(f"  - Return Cutoff   : {constraints.return_cutoff}")

    # Step 2: Scout Agent POI Discovery
    print(f"\n[Step 1: Scout Agent Execution]")
    candidates = search_live_pois(constraints.origin, constraints.vibe, constraints.budget_usd)
    if not candidates:
        candidates = query_poi_database(constraints.origin, constraints.vibe, constraints.budget_usd)
    print(f"  - Candidates Located : {len(candidates)}")
    for i, c in enumerate(candidates[:3], 1):
        cost_str = f"${c.estimated_admission:.2f}" if c.estimated_admission > 0 else "FREE"
        print(f"    {i}. {c.name} ({c.estimated_dwell_minutes}m dwell | Cost: {cost_str} | Coords: {c.lat:.4f}, {c.lng:.4f})")
    
    primary_candidate = candidates[0]
    print(f"  ↳ Selected Waypoint  : '{primary_candidate.name}'")

    # Step 3: Transit Agent Multi-Modal Mobility
    print(f"\n[Step 2: Transit Agent Execution]")
    transit_options, recommended_mode = calculate_multi_modal_options(
        origin_str=constraints.origin,
        dest_lat=primary_candidate.lat,
        dest_lng=primary_candidate.lng,
    )
    print(f"  - Multi-Modal Options Evaluated: {len(transit_options)}")
    for opt in transit_options:
        cost_tag = f"${opt.estimated_cost:.2f}" if opt.estimated_cost > 0 else "FREE"
        star = " ★ (Selected)" if opt.mode == recommended_mode else ""
        print(f"    - {opt.mode.capitalize():<10}: {opt.duration_minutes:>2}m | Cost: {cost_tag:>6} | {opt.details}{star}")
    
    chosen_transit = next((o for o in transit_options if o.mode == recommended_mode), transit_options[0])

    # Feasibility math
    roundtrip_transit = 2 * chosen_transit.duration_minutes
    primary_dwell = primary_candidate.estimated_dwell_minutes
    transit_cost = chosen_transit.estimated_cost
    roundtrip_transit_cost = 2 * transit_cost if chosen_transit.mode != "driving" else transit_cost
    admission_cost = primary_candidate.estimated_admission

    time_used = roundtrip_transit + primary_dwell
    slack_time = max(0, constraints.duration_minutes - time_used)
    remaining_budget = max(0.0, constraints.budget_usd - (roundtrip_transit_cost + admission_cost))

    print(f"\n[Step 3: Feasibility & Slack Calculation]")
    print(f"  - Temporal: {time_used}m used of {constraints.duration_minutes}m allotment -> Slack: {slack_time}m")
    print(f"  - Fiscal  : ${roundtrip_transit_cost + admission_cost:.2f} allocated of ${constraints.budget_usd:.2f} cap -> Reserves: ${remaining_budget:.2f}")

    # Step 4: Budget & Meal Agent Opportunistic Dining
    print(f"\n[Step 4: Budget & Meal Agent Execution]")
    if slack_time >= 45 and remaining_budget >= 15.0:
        dining_candidates = [s for s in SIT_DOWN_OPTIONS if s["cost"] <= remaining_budget and s["dwell"] <= (slack_time - 10)]
        chosen_meal = dining_candidates[0] if dining_candidates else SIT_DOWN_OPTIONS[0]
        meal_result = MealResult(
            session_id=session_id,
            recommended=True,
            spot_name=chosen_meal["name"],
            estimated_cost=chosen_meal["cost"],
            dwell_mins=chosen_meal["dwell"],
            reasoning=f"Optimal slack ({slack_time}m) allows sit-down culinary checkpoint: {chosen_meal['reasoning']}",
            perk=chosen_meal["perk"],
        )
        print(f"  - Recommendation: Sit-Down Dining -> {chosen_meal['name']} (${chosen_meal['cost']:.2f})")
    elif slack_time >= 20 and remaining_budget >= 4.50:
        snack_candidates = [s for s in SNACK_OPTIONS if s["cost"] <= remaining_budget and s["dwell"] <= (slack_time - 5)]
        chosen_snack = snack_candidates[0] if snack_candidates else SNACK_OPTIONS[0]
        meal_result = MealResult(
            session_id=session_id,
            recommended=True,
            spot_name=chosen_snack["name"],
            estimated_cost=chosen_snack["cost"],
            dwell_mins=chosen_snack["dwell"],
            reasoning=f"Tactical slack ({slack_time}m) allows quick supply drop: {chosen_snack['reasoning']}",
            perk=chosen_snack["perk"],
        )
        print(f"  - Recommendation: Grab-and-go Snack -> {chosen_snack['name']} (${chosen_snack['cost']:.2f})")
    else:
        meal_result = MealResult(
            session_id=session_id,
            recommended=False,
            spot_name=None,
            estimated_cost=0.0,
            dwell_mins=0,
            reasoning="Schedule or funds are tightly allocated; preserving return deadline.",
            perk=None,
        )
        print(f"  - Recommendation: No meal added (slack: {slack_time}m, reserves: ${remaining_budget:.2f})")

    # Step 5: Final Synthesis
    print(f"\n[Step 5: RPG Sidequest Log Synthesis]")
    log_output = render_multiagent_rpg_log(
        constraints=constraints,
        candidate=primary_candidate,
        chosen_transit=chosen_transit,
        all_transit_options=transit_options,
        meal_res=meal_result,
    )
    print("\n" + "=" * 30 + " SYNTHESIZED SIDEQUEST LOG " + "=" * 30)
    print(log_output)
    print("=" * 87 + "\n")


def is_bureau_running(port: int = 8000) -> bool:
    """Check if the local Bureau server is listening on port 8000."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def run_live_test(prompt: str):
    """Run live test against running Bureau server via simulate_asi1_chat."""
    import subprocess
    print("=" * 75)
    print(" 📡 [LIVE INTER-AGENT MESSAGE PASSING TEST]")
    print("=" * 75)
    print("Testing asynchronous message dispatch across all 4 agents in Bureau:")
    print("  1. User -> Orchestrator      : ChatMessage (ACP Protocol)")
    print("  2. Orchestrator -> User      : ChatAcknowledgement (Instant Delivery Confirmation)")
    print("  3. Orchestrator -> Scout     : ScoutQuery (schemas.ScoutQuery)")
    print("  4. Scout -> Orchestrator     : ScoutResult (schemas.ScoutResult)")
    print("  5. Orchestrator -> Transit   : TransitQuery (schemas.TransitQuery)")
    print("  6. Transit -> Orchestrator   : TransitResult (schemas.TransitResult)")
    print("  7. Orchestrator -> Budget    : MealQuery (schemas.MealQuery)")
    print("  8. Budget -> Orchestrator    : MealResult (schemas.MealResult)")
    print("  9. Orchestrator -> User      : ChatMessage with Multi-Agent Itinerary")
    print("-" * 75)
    cmd = [sys.executable, "simulate_asi1_chat.py", prompt]
    subprocess.run(cmd)


def main():
    custom_prompt = next((arg for arg in sys.argv[1:] if not arg.startswith("--")), None)

    # 1. If Bureau is running or user passed --live, execute live message-passing test
    if "--live" in sys.argv or is_bureau_running(8000):
        prompt_to_use = custom_prompt or SAMPLE_TESTS[0][1]
        print("\n>>> Detected active Bureau on port 8000. Running live inter-agent message passing test...")
        run_live_test(prompt_to_use)
    else:
        print("\n>>> Bureau not detected on port 8000. (Tip: run 'python run.py' to launch live Bureau)")

    # 2. Run the detailed multi-scenario test suite
    print("\n" + "=" * 75)
    print(" 📋 [MULTI-SCENARIO PIPELINE TRACE]")
    print("=" * 75)
    for title, prompt in SAMPLE_TESTS:
        print(f"\n>>> Scenario: {title}")
        run_pipeline_step_by_step(prompt)


if __name__ == "__main__":
    main()
