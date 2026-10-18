"""
transit_agent.py: Transit & Mobility Agent for multi-modal route calculation.

Subagent in Quest Orchestrator Bureau:
- Receives: TransitQuery
- Replies: TransitResult with multi-modal TransitOption models (walking, transit, driving, rideshare)
- Features: Google Maps Routes API integration with realistic Haversine LA mobility fallback.
"""

import os
import sys
import math
import requests
from typing import List, Dict, Tuple
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from uagents import Agent, Context, Protocol
from schemas import TransitQuery, TransitResult, TransitOption

TRANSIT_SEED = os.getenv("TRANSIT_SEED_PHRASE", "transit-subagent-seed-phrase-la-hacks-quest").strip()

transit_agent = Agent(
    name="Transit Agent",
    seed=TRANSIT_SEED,
)

# Known neighborhood centroids in Los Angeles (lat, lng)
NEIGHBORHOOD_COORDS: Dict[str, Tuple[float, float]] = {
    "westwood": (34.0689, -118.4452),
    "ucla": (34.0689, -118.4452),
    "santa monica": (34.0195, -118.4912),
    "venice": (33.9850, -118.4695),
    "koreatown": (34.0628, -118.3005),
    "ktown": (34.0628, -118.3005),
    "downtown": (34.0522, -118.2437),
    "dtla": (34.0522, -118.2437),
    "sawtelle": (34.0416, -118.4468),
    "hollywood": (34.1016, -118.3268),
    "silver lake": (34.0869, -118.2702),
    "culver city": (34.0211, -118.3965),
    "pasadena": (34.1478, -118.1445),
}


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two GPS coordinates in miles."""
    r_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r_miles * c


def get_origin_coords(origin_text: str) -> Tuple[float, float]:
    """Resolve origin string to coordinates."""
    origin_lower = origin_text.lower()
    for name, coords in NEIGHBORHOOD_COORDS.items():
        if name in origin_lower:
            return coords
    return NEIGHBORHOOD_COORDS["westwood"]


def calculate_routes_api(origin_coords: Tuple[float, float], dest_lat: float, dest_lng: float) -> List[TransitOption]:
    """Optional Google Maps Routes API call if API key exists."""
    gmaps_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not gmaps_key:
        return []

    try:
        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": gmaps_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        }
        body = {
            "origin": {"location": {"latLng": {"latitude": origin_coords[0], "longitude": origin_coords[1]}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lng}}},
            "travelMode": "TRANSIT",
        }
        res = requests.post(url, headers=headers, json=body, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            routes = data.get("routes", [])
            if routes:
                duration_sec = int(routes[0].get("duration", "900s").replace("s", ""))
                return [
                    TransitOption(
                        mode="transit",
                        duration_minutes=max(10, duration_sec // 60),
                        estimated_cost=1.75,
                        details="Live Google Transit Route (LA Metro)",
                    )
                ]
    except Exception:
        pass
    return []


def calculate_multi_modal_options(origin_str: str, dest_lat: float, dest_lng: float) -> Tuple[List[TransitOption], str]:
    """Calculates multi-modal travel options using realistic LA speed and transit models."""
    origin_lat, origin_lng = get_origin_coords(origin_str)

    # Calculate road distance with LA circuity factor (~1.25x haversine)
    direct_dist = haversine_miles(origin_lat, origin_lng, dest_lat, dest_lng)
    road_miles = max(0.2, direct_dist * 1.25)

    options: List[TransitOption] = []

    # 1. Walking Mode (3.1 mph -> 19.3 min/mile)
    walk_mins = int(road_miles * 19.3)
    if walk_mins <= 40 or road_miles <= 1.5:
        options.append(
            TransitOption(
                mode="walking",
                duration_minutes=max(5, walk_mins),
                estimated_cost=0.0,
                details=f"Pedestrian stroll (~{road_miles:.1f} mi)",
            )
        )

    # 2. Public Transit Mode (LA Metro Bus / Rail: 12.5 mph avg + 8m headway buffer)
    transit_mins = int((road_miles / 12.5) * 60) + 8
    options.append(
        TransitOption(
            mode="transit",
            duration_minutes=max(10, transit_mins),
            estimated_cost=1.75,
            details="LA Metro Bus / Rail (TAP Card)",
        )
    )

    # 3. Driving Mode (22 mph city traffic + 5m parking/ingress buffer)
    drive_mins = int((road_miles / 22.0) * 60) + 5
    parking_fee = 6.0 if "downtown" in origin_str.lower() or "santa monica" in origin_str.lower() else 3.0
    drive_cost = round(parking_fee + (road_miles * 0.45), 2)
    options.append(
        TransitOption(
            mode="driving",
            duration_minutes=max(7, drive_mins),
            estimated_cost=drive_cost,
            details=f"Personal Vehicle (Metered parking: ${parking_fee:.2f})",
        )
    )

    # 4. Rideshare Mode (Uber / Lyft: $3.25 base + $1.85/mi + $0.40/min)
    rideshare_mins = int((road_miles / 22.0) * 60) + 4
    rideshare_cost = round(3.25 + (road_miles * 1.85) + (rideshare_mins * 0.40), 2)
    options.append(
        TransitOption(
            mode="rideshare",
            duration_minutes=max(6, rideshare_mins),
            estimated_cost=rideshare_cost,
            details=f"Rideshare Express (~{rideshare_mins}m door-to-door)",
        )
    )

    # Select recommended mode
    if road_miles <= 0.8:
        recommended = "walking"
    elif road_miles <= 4.0:
        recommended = "transit"
    else:
        recommended = "driving"

    return options, recommended


transit_proto = Protocol(name="TransitProtocol", version="1.0.0")


@transit_proto.on_message(TransitQuery)
async def handle_transit_query(ctx: Context, sender: str, msg: TransitQuery):
    ctx.logger.info(
        f"🚦 TransitQuery from {sender} [Session: {msg.session_id}] | "
        f"Origin: '{msg.origin}' -> Dest: ({msg.destination_lat:.4f}, {msg.destination_lng:.4f})"
    )

    # 1. Try Google Maps API if configured
    options = calculate_routes_api((34.0689, -118.4452), msg.destination_lat, msg.destination_lng)

    # 2. Comprehensive multi-modal mobility calculation
    if not options or len(options) < 2:
        options, recommended = calculate_multi_modal_options(msg.origin, msg.destination_lat, msg.destination_lng)
    else:
        recommended = options[0].mode

    ctx.logger.info(
        f"🛣️ Calculated {len(options)} transit options. Recommended mode: '{recommended}'. Replying to Orchestrator..."
    )
    reply = TransitResult(
        session_id=msg.session_id,
        candidate_id=msg.candidate_id,
        options=options,
        recommended_mode=recommended,
    )
    await ctx.send(sender, reply)


transit_agent.include(transit_proto)


if __name__ == "__main__":
    transit_agent.run()
