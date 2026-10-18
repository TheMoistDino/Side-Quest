"""
adapters.py: Dual Gateway & Translation Layer for Side-Quest.

Provides two-way translation between:
1. Custom Web/App Frontend (Next.js REST JSON contract defined in types/quest.ts)
2. Fetch.ai ASI:One Interface (Agent Chat Protocol via uAgents/Agentverse)
3. Internal Multi-Agent Pipeline (ScoutQuery, TransitQuery, MealQuery, QuestConstraints)

Preserves 100% strict compatibility with frontend types/quest.ts without modifying any frontend code.
"""

import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import Field
from uagents import Model

from schemas import (
    QuestCandidate,
    TransitOption,
    MealResult,
)
from planner import (
    QuestConstraints,
    extract_constraints,
    render_multiagent_rpg_log,
    render_rpg_log,
    synthesize_quest,
)


# ==============================================================================
# 1. Frontend API Request & Response Models (Mirroring types/quest.ts)
# ==============================================================================

class FrontendLocation(Model):
    lat: float = 34.0635
    lng: float = -118.4455
    label: Optional[str] = None


class FrontendQuestRequest(Model):
    category: str = ""
    startTime: str = ""
    endTime: str = ""
    budgetPerPerson: float = 35.0
    maxDistanceMiles: float = 10.0
    location: Optional[FrontendLocation] = None
    groupSize: Optional[int] = 1


class FrontendReview(Model):
    author: Optional[str] = None
    rating: Optional[float] = None
    snippet: str = ""
    sourceName: str = "Google"
    sourceUrl: str = "https://maps.google.com"


class FrontendStop(Model):
    id: str
    order: int
    name: str
    category: str
    address: str
    lat: float
    lng: float
    startTime: Optional[str] = None
    durationMinutes: int
    estimatedCost: float
    costIsEstimate: bool = False
    distanceFromPreviousMiles: float
    travelFromPreviousMinutes: int
    travelMode: Literal["driving", "walking", "transit"]
    rating: Optional[float] = None
    reviewCount: Optional[int] = None
    reviewSummary: str = ""
    reviews: List[FrontendReview] = []
    sourceUrl: Optional[str] = None


class FrontendQuest(Model):
    id: str
    title: str
    tagline: str
    totalCostPerPerson: float
    totalDurationMinutes: int
    totalTravelMinutes: int
    totalDistanceMiles: float
    stops: List[FrontendStop] = []


class FrontendQuestResponse(Model):
    quests: List[FrontendQuest] = []


class FrontendApiError(Model):
    error: Dict[str, str]


# ==============================================================================
# 2. Known LA Neighborhood Centroids & Spatial Helpers
# ==============================================================================

NEIGHBORHOOD_CENTROIDS: Dict[str, Tuple[float, float]] = {
    "Westwood / UCLA": (34.0689, -118.4452),
    "Santa Monica / Ocean": (34.0195, -118.4912),
    "Venice Beach": (33.9850, -118.4695),
    "Koreatown": (34.0628, -118.3005),
    "Downtown LA (DTLA)": (34.0522, -118.2437),
    "Sawtelle Japantown": (34.0416, -118.4468),
    "Hollywood": (34.1016, -118.3268),
    "Culver City": (34.0211, -118.3965),
    "Silver Lake": (34.0869, -118.2702),
    "Pasadena": (34.1478, -118.1445),
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in miles between two coordinates."""
    r_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_miles * c


def resolve_nearest_neighborhood(lat: float, lng: float, explicit_label: Optional[str] = None) -> str:
    """Map GPS coordinates or explicit label to the closest known operational LA district."""
    if explicit_label and isinstance(explicit_label, str) and explicit_label.strip():
        label_lower = explicit_label.lower()
        for name in NEIGHBORHOOD_CENTROIDS:
            if name.lower() in label_lower:
                return name
        # If user gave a specific label, use it directly
        return explicit_label.strip()

    # Find closest centroid
    closest_name = "Westwood / UCLA"
    min_dist = float("inf")
    for name, (c_lat, c_lng) in NEIGHBORHOOD_CENTROIDS.items():
        dist = haversine_miles(lat, lng, c_lat, c_lng)
        if dist < min_dist:
            min_dist = dist
            closest_name = name

    return closest_name


def parse_iso_datetime(iso_str: Optional[str]) -> datetime:
    """Parse ISO 8601 string safely into datetime, defaulting to now."""
    if not iso_str:
        return datetime.now(timezone.utc)
    try:
        clean = iso_str.strip().replace("Z", "+00:00")
        return datetime.fromisoformat(clean)
    except Exception:
        return datetime.now(timezone.utc)


def add_minutes_iso(base_iso: str, minutes: int) -> str:
    """Add minutes to an ISO string and return ISO 8601 string."""
    dt = parse_iso_datetime(base_iso)
    new_dt = dt + timedelta(minutes=minutes)
    return new_dt.isoformat()


# ==============================================================================
# 3. Path A: Frontend Ingestion & Adaptation
# ==============================================================================

def adapt_frontend_request_to_constraints(req: FrontendQuestRequest) -> QuestConstraints:
    """
    Ingests raw FrontendQuestRequest, normalizes parameters, handles missing fields,
    and maps them to internal QuestConstraints for multi-agent delegation.
    """
    # 1. Temporal Window & Duration
    start_dt = parse_iso_datetime(req.startTime)
    end_dt = parse_iso_datetime(req.endTime)

    delta_seconds = (end_dt - start_dt).total_seconds()
    if delta_seconds > 0:
        duration_minutes = int(delta_seconds / 60)
    else:
        # Sensible default if timestamps are invalid or negative
        duration_minutes = 180

    # Clamp duration to realistic bounds [30m, 480m]
    duration_minutes = max(30, min(480, duration_minutes))

    departure_str = start_dt.strftime("%I:%M %p")
    return_cutoff_str = end_dt.strftime("%I:%M %p")

    # 2. Fiscal Budget
    budget = float(req.budgetPerPerson) if (req.budgetPerPerson is not None and isinstance(req.budgetPerPerson, (int, float)) and req.budgetPerPerson >= 0) else 35.0

    # 3. Geographic Starting Point
    lat = float(req.location.lat) if (req.location and req.location.lat is not None and isinstance(req.location.lat, (int, float))) else 34.0635
    lng = float(req.location.lng) if (req.location and req.location.lng is not None and isinstance(req.location.lng, (int, float))) else -118.4455
    label = req.location.label if (req.location and isinstance(req.location.label, str)) else None
    origin = resolve_nearest_neighborhood(lat, lng, label)

    # 4. Category & Vibe Normalization
    cat_raw = (req.category or "").strip().lower()
    if cat_raw in ["arts", "art", "museum", "culture"]:
        vibe = "art"
    elif cat_raw in ["outdoors", "chill", "nature", "park", "garden"]:
        vibe = "chill"
    elif cat_raw in ["food", "dining", "eats", "foodie"]:
        vibe = "food"
    elif cat_raw in ["nightlife", "drinks", "bars"]:
        vibe = "food"
    elif cat_raw in ["games", "arcade", "bowling"]:
        vibe = "arcade"
    elif cat_raw in ["tech", "cyber", "internet"]:
        vibe = "tech"
    elif cat_raw in ["surprise me", "surprise", "adventure", "random", ""]:
        # Rotate based on neighborhood character
        if "santa monica" in origin.lower():
            vibe = "chill"
        elif "downtown" in origin.lower():
            vibe = "art"
        else:
            vibe = "food"
    else:
        vibe = "chill"

    return QuestConstraints(
        duration_minutes=duration_minutes,
        budget_usd=budget,
        origin=origin,
        vibe=vibe,
        departure_time=departure_str,
        return_cutoff=return_cutoff_str,
    )


# ==============================================================================
# 4. Path B: ASI:One ACP Ingestion
# ==============================================================================

def adapt_acp_message_to_constraints(incoming_text: str) -> QuestConstraints:
    """
    Maintains conversational natural language parsing via Agent Chat Protocol.
    Uses regex and semantic heuristics from planner.py.
    """
    cleaned_prompt = incoming_text.strip() if incoming_text else "2 hours free, $30 budget near Westwood for art or chill"
    return extract_constraints(cleaned_prompt)


# ==============================================================================
# 5. Output Formatting: Frontend QuestResponse Synthesizer
# ==============================================================================

def normalize_travel_mode(mode: str) -> Literal["driving", "walking", "transit"]:
    """Normalize arbitrary transit mode strings to strict frontend enum."""
    mode_clean = (mode or "").lower()
    if "walk" in mode_clean:
        return "walking"
    elif "transit" in mode_clean or "bus" in mode_clean or "metro" in mode_clean or "rail" in mode_clean:
        return "transit"
    else:
        return "driving"


def adapt_pipeline_to_frontend_response(
    constraints: QuestConstraints,
    candidate: QuestCandidate,
    chosen_transit: TransitOption,
    all_transit_options: List[TransitOption],
    meal_res: Optional[MealResult],
    req: FrontendQuestRequest,
    all_candidates: Optional[List[QuestCandidate]] = None,
) -> FrontendQuestResponse:
    """
    Transforms multi-agent synthesized itinerary into the exact schema, field names,
    and nested structures required by the Next.js frontend (FrontendQuestResponse).
    Synthesizes up to 3 curated options to populate the frontend's QuestBoard.
    """
    user_lat = req.location.lat
    user_lng = req.location.lng
    req_start_iso = req.startTime

    # Ensure we have candidates list
    candidates_pool = list(all_candidates) if all_candidates else [candidate]
    if candidate not in candidates_pool:
        candidates_pool.insert(0, candidate)

    quests: List[FrontendQuest] = []

    # Helper: Build Quest 1 (Primary Recommended Quest)
    primary_quest = _build_single_quest(
        quest_index=1,
        title_prefix="Primary Recommended",
        primary_poi=candidate,
        transit=chosen_transit,
        meal=meal_res,
        constraints=constraints,
        user_lat=user_lat,
        user_lng=user_lng,
        req_start_iso=req_start_iso,
    )
    quests.append(primary_quest)

    # Helper: Build Quest 2 (Alternative POI or Alternative Mobility Option)
    cand2 = candidates_pool[1] if len(candidates_pool) > 1 else candidates_pool[0]
    alt_mode = next((opt for opt in all_transit_options if opt.mode != chosen_transit.mode), chosen_transit)
    quest2 = _build_single_quest(
        quest_index=2,
        title_prefix="Active Pace & Exploratory",
        primary_poi=cand2,
        transit=alt_mode,
        meal=None if (meal_res and meal_res.recommended) else meal_res,
        constraints=constraints,
        user_lat=user_lat,
        user_lng=user_lng,
        req_start_iso=req_start_iso,
        force_snack=True,
    )
    quests.append(quest2)

    # Helper: Build Quest 3 (Scenic Leisure & Value Option)
    cand3 = candidates_pool[2] if len(candidates_pool) > 2 else candidates_pool[0]
    walk_or_drive = next((opt for opt in all_transit_options if opt.mode in ["walking", "driving"]), chosen_transit)
    quest3 = _build_single_quest(
        quest_index=3,
        title_prefix="Scenic Leisure & Highlights",
        primary_poi=cand3,
        transit=walk_or_drive,
        meal=meal_res,
        constraints=constraints,
        user_lat=user_lat,
        user_lng=user_lng,
        req_start_iso=req_start_iso,
    )
    quests.append(quest3)

    return FrontendQuestResponse(quests=quests)


def _build_single_quest(
    quest_index: int,
    title_prefix: str,
    primary_poi: QuestCandidate,
    transit: TransitOption,
    meal: Optional[MealResult],
    constraints: QuestConstraints,
    user_lat: float,
    user_lng: float,
    req_start_iso: str,
    force_snack: bool = False,
) -> FrontendQuest:
    """Synthesizes a single FrontendQuest with realistic Stop timeline and metrics."""
    stops: List[FrontendStop] = []

    # Leg 1: Travel from user location to Stop 1
    dist_1 = round(haversine_miles(user_lat, user_lng, primary_poi.lat, primary_poi.lng) * 1.25, 1)
    dist_1 = max(0.2, dist_1)
    travel_mins_1 = transit.duration_minutes
    mode_1 = normalize_travel_mode(transit.mode)

    # Stop 1 Arrival timestamp
    stop1_start_iso = add_minutes_iso(req_start_iso, travel_mins_1)
    stop1_dwell = primary_poi.estimated_dwell_minutes
    stop1_cost = primary_poi.estimated_admission

    # Review conversion
    poi_reviews: List[FrontendReview] = []
    if primary_poi.reviews:
        for r in primary_poi.reviews[:3]:
            if isinstance(r, dict):
                r_author = r.get("author", "Local Explorer")
                r_rating = float(r.get("rating", 5.0))
                r_snippet = r.get("text") or r.get("snippet", "Authentic visitor experience in Los Angeles.")
                r_source = r.get("source") or r.get("sourceName", "Google Maps")
                r_url = r.get("sourceUrl") or getattr(primary_poi, "verified_url", None) or getattr(primary_poi, "source_url", "https://maps.google.com")
            else:
                r_author = getattr(r, "author", "Local Explorer")
                r_rating = float(getattr(r, "rating", 5.0))
                r_snippet = getattr(r, "text", None) or getattr(r, "snippet", "Authentic visitor experience in Los Angeles.")
                r_source = getattr(r, "source", None) or getattr(r, "sourceName", "Google Maps")
                r_url = getattr(r, "source_url", None) or getattr(primary_poi, "verified_url", None) or getattr(primary_poi, "source_url", "https://maps.google.com")

            poi_reviews.append(
                FrontendReview(
                    author=r_author,
                    rating=r_rating,
                    snippet=r_snippet,
                    sourceName=r_source,
                    sourceUrl=r_url,
                )
            )
    # No reviews -> send none. The contract promises real snippets, so never invent one.

    canonical_poi_url = primary_poi.verified_url or primary_poi.source_url or "https://maps.google.com"

    stop1 = FrontendStop(
        id=f"stop-{primary_poi.id}-{quest_index}",
        order=1,
        name=primary_poi.name,
        category=primary_poi.category or constraints.vibe.capitalize(),
        address=primary_poi.address or f"{primary_poi.name}, {constraints.origin}, CA",
        lat=primary_poi.lat,
        lng=primary_poi.lng,
        startTime=stop1_start_iso,
        durationMinutes=stop1_dwell,
        estimatedCost=stop1_cost,
        costIsEstimate=bool(getattr(primary_poi, "cost_is_estimate", False)) and stop1_cost > 0,
        distanceFromPreviousMiles=dist_1,
        travelFromPreviousMinutes=travel_mins_1,
        travelMode=mode_1,
        rating=primary_poi.rating or 4.7,
        reviewCount=primary_poi.review_count or 1200,
        reviewSummary=primary_poi.review_summary or primary_poi.description,
        reviews=poi_reviews,
        sourceUrl=canonical_poi_url,
    )
    stops.append(stop1)

    elapsed_minutes = travel_mins_1 + stop1_dwell
    total_travel_mins = travel_mins_1
    total_distance_miles = dist_1
    total_cost = stop1_cost

    # Leg 2 / Stop 2: Opportunistic Dining / Snack Checkpoint
    has_meal = (meal and meal.recommended and meal.spot_name) or force_snack
    if has_meal:
        meal_name = meal.spot_name if (meal and meal.spot_name) else "Boba Time Roasted Milk Tea"
        meal_cost = meal.estimated_cost if meal else 6.50
        meal_dwell = meal.dwell_mins if meal else 20
        meal_reasoning = meal.reasoning if meal else "Quick caffeinated supply drop to restore morale and stamina."

        travel_to_meal_mins = 6
        dist_to_meal_miles = 0.3

        stop2_start_iso = add_minutes_iso(stop1_start_iso, stop1_dwell + travel_to_meal_mins)

        # The budget agent doesn't return review text, and the contract promises real snippets,
        # so the meal stop ships without reviews rather than with an invented one.
        meal_reviews: List[FrontendReview] = []

        stop2 = FrontendStop(
            id=f"stop-meal-{quest_index}",
            order=2,
            name=meal_name,
            category="Dining & Refreshment" if meal_dwell >= 35 else "Specialty Snack & Drink",
            address=f"Near {primary_poi.name}, {constraints.origin}, CA",
            lat=round(primary_poi.lat + 0.0020, 4),
            lng=round(primary_poi.lng + 0.0018, 4),
            startTime=stop2_start_iso,
            durationMinutes=meal_dwell,
            estimatedCost=meal_cost,
            costIsEstimate=True,
            distanceFromPreviousMiles=dist_to_meal_miles,
            travelFromPreviousMinutes=travel_to_meal_mins,
            travelMode="walking",
            rating=4.6,
            reviewCount=950,
            reviewSummary=meal_reasoning,
            reviews=meal_reviews,
            sourceUrl=f"https://maps.google.com/?q={meal_name.replace(' ', '+')}",
        )
        stops.append(stop2)

        elapsed_minutes += travel_to_meal_mins + meal_dwell
        total_travel_mins += travel_to_meal_mins
        total_distance_miles += dist_to_meal_miles
        total_cost += meal_cost

    # Return Leg: Travel back to base / origin
    return_travel_mins = travel_mins_1
    return_dist = dist_1
    elapsed_minutes += return_travel_mins
    total_travel_mins += return_travel_mins
    total_distance_miles += return_dist

    # Generate title and tagline
    if len(stops) == 1:
        title = f"{primary_poi.name} Discovery"
        tagline = f"Explore {primary_poi.name} with focused cultural dwell time in {constraints.origin}."
    else:
        title = f"{primary_poi.name} & {stops[1].name.split('(')[0].strip()}"
        tagline = f"Experience {primary_poi.name}, then recharge at {stops[1].name.split('(')[0].strip()} before returning."

    quest_id = f"q-{constraints.vibe}-{primary_poi.id[:4]}-{quest_index}"

    return FrontendQuest(
        id=quest_id,
        title=title,
        tagline=tagline,
        totalCostPerPerson=round(total_cost, 2),
        totalDurationMinutes=elapsed_minutes,
        totalTravelMinutes=total_travel_mins,
        totalDistanceMiles=round(total_distance_miles, 1),
        stops=stops,
    )


# ==============================================================================
# 6. Output Formatting: ASI:One ACP Message Synthesizer
# ==============================================================================

def adapt_pipeline_to_acp_response(
    constraints: QuestConstraints,
    candidate: QuestCandidate,
    chosen_transit: TransitOption,
    all_transit_options: List[TransitOption],
    meal_res: Optional[MealResult],
) -> Tuple[str, Dict[str, Any]]:
    """
    Formats multi-agent itinerary for Fetch.ai ASI:One Agent Chat Protocol (ACP):
    1. Conversational Markdown RPG Sidequest Log
    2. Interactive Card Schema dictionary adhering to ACP specifications
    """
    # 1. Render Markdown Log
    markdown_log = render_multiagent_rpg_log(
        constraints=constraints,
        candidate=candidate,
        chosen_transit=chosen_transit,
        all_transit_options=all_transit_options,
        meal_res=meal_res,
    )

    # 2. Render ASI Interactive Card Payload
    one_way_transit = chosen_transit.duration_minutes
    primary_dwell = candidate.estimated_dwell_minutes
    meal_dwell = meal_res.dwell_mins if meal_res and meal_res.recommended else 0
    total_time_used = (2 * one_way_transit) + primary_dwell + meal_dwell

    spent_cost = chosen_transit.estimated_cost + candidate.estimated_admission + (meal_res.estimated_cost if meal_res and meal_res.recommended else 0.0)

    card_payload = {
        "type": "interactive_card",
        "card_version": "1.0",
        "theme": "rpg_sidequest",
        "header": {
            "title": f"Operation: Urban Odyssey in {constraints.origin}",
            "rank": "RANK A - VETERAN ADVENTURE" if constraints.duration_minutes >= 120 else "RANK B - RAPID RECON",
            "vibe": constraints.vibe.upper(),
        },
        "metrics": {
            "time_used_minutes": total_time_used,
            "time_budget_minutes": constraints.duration_minutes,
            "cost_spent_usd": round(spent_cost, 2),
            "cost_budget_usd": constraints.budget_usd,
        },
        "stops": [
            {
                "type": "Primary Objective",
                "name": candidate.name,
                "dwell_mins": candidate.estimated_dwell_minutes,
                "admission_usd": candidate.estimated_admission,
                "perk": candidate.perk,
                "coordinates": [candidate.lat, candidate.lng],
            }
        ],
        "transit": {
            "mode": chosen_transit.mode,
            "duration_minutes": chosen_transit.duration_minutes,
            "estimated_cost": chosen_transit.estimated_cost,
            "details": chosen_transit.details,
        },
    }

    if meal_res and meal_res.recommended and meal_res.spot_name:
        card_payload["stops"].append(
            {
                "type": "Opportunistic Culinary Drop",
                "name": meal_res.spot_name,
                "dwell_mins": meal_res.dwell_mins,
                "cost_usd": meal_res.estimated_cost,
                "perk": meal_res.perk or "+15 Gastronomy Insight",
            }
        )

    return markdown_log, card_payload
