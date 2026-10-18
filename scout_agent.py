"""
scout_agent.py: Scout Agent for POI discovery and dwell-time estimation.

Subagent in Quest Orchestrator Bureau:
- Receives: ScoutQuery
- Replies: ScoutResult with list of QuestCandidate models
- Features: Live search/API fetcher (Tavily / SerpAPI) with rich LA hotspot fallback.
"""

import os
import sys
import uuid
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from uagents import Agent, Context, Protocol
from schemas import ScoutQuery, ScoutResult, QuestCandidate

SCOUT_SEED = os.getenv("SCOUT_SEED_PHRASE", "scout-subagent-seed-phrase-la-hacks-quest").strip()

scout_agent = Agent(
    name="Scout Agent",
    seed=SCOUT_SEED,
)

# Curated catalog of LA hotspots with realistic coordinates, opening hours, admission, and perks
LA_POI_CATALOG: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "westwood": {
        "art": [
            {
                "name": "Hammer Museum Courtyard & Galleries",
                "lat": 34.0594,
                "lng": -118.4437,
                "admission": 0.0,
                "dwell": 60,
                "hours": "11:00 AM - 6:00 PM (Closed Mon)",
                "desc": "Contemporary art galleries, open-air courtyard, and free admission.",
                "perk": "+20 Cultural Wisdom, Free Admission Perk",
            },
            {
                "name": "Fowler Museum at UCLA",
                "lat": 34.0754,
                "lng": -118.4423,
                "admission": 0.0,
                "dwell": 45,
                "hours": "12:00 PM - 5:00 PM (Wed-Sun)",
                "desc": "Global arts and indigenous archaeological collections on UCLA campus.",
                "perk": "+15 Ancient Lore",
            },
        ],
        "chill": [
            {
                "name": "UCLA Mathias Botanical Garden",
                "lat": 34.0674,
                "lng": -118.4410,
                "admission": 0.0,
                "dwell": 50,
                "hours": "8:00 AM - 5:00 PM (Daily)",
                "desc": "Lush 7.5-acre forest sanctuary featuring 3,000+ species of tropical flora.",
                "perk": "+25 Mental Resilience, Stress Purge",
            },
            {
                "name": "Espresso Profeta Secret Brick Patio",
                "lat": 34.0620,
                "lng": -118.4465,
                "admission": 7.0,
                "dwell": 40,
                "hours": "7:00 AM - 6:00 PM (Daily)",
                "desc": "Artisanal velvet latte under ivy-covered brick arches.",
                "perk": "+10 Agility, Caffeine Buff",
            },
        ],
        "food": [
            {
                "name": "Diddy Riese Custom Cookie Sandwich",
                "lat": 34.0631,
                "lng": -118.4468,
                "admission": 5.0,
                "dwell": 25,
                "hours": "12:00 PM - 11:00 PM (Daily)",
                "desc": "Freshly baked warm cookies with premium Dreyer's ice cream center.",
                "perk": "+15 Sugar Rush, +10 Morale",
            },
        ],
        "tech": [
            {
                "name": "Boelter Hall 3420 (Birthplace of the Internet)",
                "lat": 34.0692,
                "lng": -118.4431,
                "admission": 0.0,
                "dwell": 35,
                "hours": "9:00 AM - 5:00 PM (Mon-Fri)",
                "desc": "Interface Message Processor #1 where the first ARPANET transmission was sent.",
                "perk": "+50 Hacker Prestige, ARPANET Genesis Artifact",
            }
        ],
    },
    "sawtelle": {
        "food": [
            {
                "name": "Tsujita LA Artisan Noodle (Sawtelle)",
                "lat": 34.0416,
                "lng": -118.4468,
                "admission": 18.0,
                "dwell": 55,
                "hours": "11:00 AM - 10:00 PM (Daily)",
                "desc": "Simmered 60-hour tonkotsu tsukemen broth with thick chewy noodles.",
                "perk": "+30 Satiety, Umami Surge",
            },
            {
                "name": "B-Sweet Dessert Bar",
                "lat": 34.0411,
                "lng": -118.4467,
                "admission": 8.0,
                "dwell": 30,
                "hours": "12:00 PM - 10:00 PM (Wed-Sun)",
                "desc": "Warm bread pudding scoops, ube crinkle treats, and cold brew.",
                "perk": "+20 Sweet Tooth Delight",
            },
        ],
        "chill": [
            {
                "name": "Giant Robot Store & GR2 Gallery",
                "lat": 34.0425,
                "lng": -118.4469,
                "admission": 0.0,
                "dwell": 40,
                "hours": "12:00 PM - 6:00 PM (Daily)",
                "desc": "Asian-American pop culture art, vinyl figurines, and indie prints.",
                "perk": "+15 Pop Culture Affinity",
            }
        ],
    },
    "santa monica": {
        "chill": [
            {
                "name": "Ocean View Park Bluff Walk",
                "lat": 34.0042,
                "lng": -118.4842,
                "admission": 0.0,
                "dwell": 50,
                "hours": "Sunrise to Sunset (Daily)",
                "desc": "Panoramic Pacific Palisades ocean bluffs with ocean breeze and sunset vista.",
                "perk": "+20 Vitality, Ocean Clarity",
            },
            {
                "name": "Dogtown Skate Park & Venice Boardwalk",
                "lat": 33.9875,
                "lng": -118.4735,
                "admission": 0.0,
                "dwell": 45,
                "hours": "6:00 AM - 8:00 PM (Daily)",
                "desc": "Legendary concrete bowls and graffiti walls on Venice Beach coastline.",
                "perk": "+15 Dexterity",
            },
        ],
        "art": [
            {
                "name": "Bergamot Station Arts Center",
                "lat": 34.0298,
                "lng": -118.4687,
                "admission": 0.0,
                "dwell": 65,
                "hours": "10:00 AM - 6:00 PM (Tue-Sat)",
                "desc": "Historic railroad depot converted into 20+ independent contemporary art galleries.",
                "perk": "+30 Aesthetic Perception",
            }
        ],
        "food": [
            {
                "name": "Bay Cities Italian Deli Godmother",
                "lat": 34.0192,
                "lng": -118.4878,
                "admission": 15.0,
                "dwell": 35,
                "hours": "9:00 AM - 6:00 PM (Tue-Sun)",
                "desc": "World-famous crusty Italian roll loaded with Genoa salami, mortadella, and peppers.",
                "perk": "+40 Stamina Reserve",
            }
        ],
    },
    "koreatown": {
        "chill": [
            {
                "name": "Koreatown Pavilion Garden (Da Wool Jung)",
                "lat": 34.0591,
                "lng": -118.3005,
                "admission": 0.0,
                "dwell": 40,
                "hours": "Sunrise - 8:00 PM (Daily)",
                "desc": "Traditional Joseon dynasty open-air pavilion built by South Korean master craftsmen.",
                "perk": "+25 Cultural Harmony, Zen Calm",
            },
            {
                "name": "Chapman Plaza Historic Castle Courtyard",
                "lat": 34.0624,
                "lng": -118.2982,
                "admission": 0.0,
                "dwell": 35,
                "hours": "10:00 AM - 11:00 PM (Daily)",
                "desc": "1929 Spanish Colonial Revival castle with neon sign installations.",
                "perk": "+15 Architectural Vision",
            },
        ],
        "food": [
            {
                "name": "Sun Nong Dan Midnight Galbi Jjim",
                "lat": 34.0628,
                "lng": -118.2974,
                "admission": 28.0,
                "dwell": 60,
                "hours": "Open 24 Hours",
                "desc": "Braised beef short rib stew torched with thick melted cheese table-side.",
                "perk": "+60 Strength, Legendary Feast",
            },
        ],
        "arcade": [
            {
                "name": "Shatto 39 Neon Bowling & Arcade",
                "lat": 34.0658,
                "lng": -118.2921,
                "admission": 15.0,
                "dwell": 50,
                "hours": "11:00 AM - 1:00 AM (Daily)",
                "desc": "Vintage retro bowling lanes with glowing neon lighting and arcade cabinets.",
                "perk": "+25 Precision, Neon Reflexes",
            }
        ],
    },
    "downtown la": {
        "art": [
            {
                "name": "The Broad Infinity Mirror & Pop Art",
                "lat": 34.0544,
                "lng": -118.2505,
                "admission": 0.0,
                "dwell": 75,
                "hours": "11:00 AM - 5:00 PM (Tue-Sun)",
                "desc": "Yayoi Kusama's celestial reflections and iconic Warhol/Basquiat canvases.",
                "perk": "+35 Cosmic Perspective, Visionary Sight",
            },
            {
                "name": "The Last Bookstore Labyrinth",
                "lat": 34.0478,
                "lng": -118.2498,
                "admission": 5.0,
                "dwell": 45,
                "hours": "11:00 AM - 8:00 PM (Daily)",
                "desc": "Spiraling literary book tunnels, hidden vaults, and vintage vinyl records.",
                "perk": "+20 Bibliophile Intellect",
            },
        ],
        "food": [
            {
                "name": "Grand Central Market Food Odyssey",
                "lat": 34.0507,
                "lng": -118.2488,
                "admission": 16.0,
                "dwell": 45,
                "hours": "8:00 AM - 9:00 PM (Daily)",
                "desc": "Historic 1917 food hall with tacos, brioche sandwiches, and gourmet coffee.",
                "perk": "+25 Gastronomy Insight",
            },
        ],
        "chill": [
            {
                "name": "Angels Flight Historic Funicular",
                "lat": 34.0514,
                "lng": -118.2502,
                "admission": 1.0,
                "dwell": 25,
                "hours": "6:45 AM - 10:00 PM (Daily)",
                "desc": "Ride the world's shortest railway climbing Bunker Hill since 1901.",
                "perk": "+10 Nostalgia Charm",
            }
        ],
    },
}


def search_live_pois(area: str, category: str, max_admission: float) -> List[QuestCandidate]:
    """Optional live search API fetcher using Tavily or SerpAPI if configured."""
    tavily_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not tavily_key:
        return []

    try:
        query = f"top {category} attractions in {area} Los Angeles opening hours ticket price"
        res = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": tavily_key, "query": query, "search_depth": "basic", "max_results": 3},
            timeout=3.0,
        )
        if res.status_code == 200:
            data = res.json()
            candidates = []
            for item in data.get("results", []):
                candidates.append(
                    QuestCandidate(
                        id=str(uuid.uuid4())[:8],
                        name=item.get("title", f"{area} Attraction"),
                        lat=34.0522,
                        lng=-118.2437,
                        estimated_admission=min(max_admission, 10.0),
                        estimated_dwell_minutes=45,
                        opening_hours="10:00 AM - 7:00 PM",
                        description=item.get("content", "")[:120] + "...",
                        perk="+20 Live Discovery Bonus",
                    )
                )
            return candidates
    except Exception:
        pass
    return []


def query_poi_database(area: str, category: str, max_admission: float) -> List[QuestCandidate]:
    """Retrieve candidates from enriched local POI database filtered by area, category, and budget."""
    area_clean = area.lower()
    cat_clean = category.lower()

    # Determine region key
    if "santa monica" in area_clean or "venice" in area_clean:
        reg_key = "santa monica"
    elif "koreatown" in area_clean or "ktown" in area_clean:
        reg_key = "koreatown"
    elif "downtown" in area_clean or "dtla" in area_clean:
        reg_key = "downtown la"
    elif "sawtelle" in area_clean:
        reg_key = "sawtelle"
    else:
        reg_key = "westwood"

    region = LA_POI_CATALOG.get(reg_key, LA_POI_CATALOG["westwood"])

    # Match category
    matched_items = region.get(cat_clean, [])
    if not matched_items:
        # Fallback to any category
        for items in region.values():
            matched_items.extend(items)

    candidates: List[QuestCandidate] = []
    for item in matched_items:
        if item["admission"] <= max_admission or max_admission == 0.0:
            candidates.append(
                QuestCandidate(
                    id=str(uuid.uuid4())[:8],
                    name=item["name"],
                    lat=item["lat"],
                    lng=item["lng"],
                    estimated_admission=item["admission"],
                    estimated_dwell_minutes=item["dwell"],
                    opening_hours=item["hours"],
                    description=item["desc"],
                    perk=item["perk"],
                )
            )

    # If no candidate fits strictly under budget, provide zero-cost exploration
    if not candidates:
        centroid_coords = {
            "westwood": (34.0689, -118.4452),
            "santa monica": (34.0195, -118.4912),
            "koreatown": (34.0628, -118.3005),
            "downtown la": (34.0522, -118.2437),
            "sawtelle": (34.0416, -118.4468),
        }
        lat, lng = centroid_coords.get(reg_key, (34.0689, -118.4452))
        candidates.append(
            QuestCandidate(
                id=str(uuid.uuid4())[:8],
                name=f"Historic Architectural Walk around {area}",
                lat=lat,
                lng=lng,
                estimated_admission=0.0,
                estimated_dwell_minutes=45,
                opening_hours="Open 24/7",
                description=f"Explore hidden open courtyards and historic street art in {area}.",
                perk="+15 Urban Cartographer EXP, Zero Cost Mastery",
            )
        )

    return candidates


scout_proto = Protocol(name="ScoutProtocol", version="1.0.0")


@scout_proto.on_message(ScoutQuery)
async def handle_scout_query(ctx: Context, sender: str, msg: ScoutQuery):
    ctx.logger.info(
        f"🔭 ScoutQuery from {sender} [Session: {msg.session_id}] | "
        f"Area: '{msg.query_area}', Category: '{msg.category}', Max Admission: ${msg.max_admission:.2f}"
    )

    # 1. Try live API if configured
    candidates = search_live_pois(msg.query_area, msg.category, msg.max_admission)

    # 2. Use comprehensive POI database
    if not candidates:
        candidates = query_poi_database(msg.query_area, msg.category, msg.max_admission)

    ctx.logger.info(f"✨ Found {len(candidates)} candidates for {msg.query_area}. Replying to Orchestrator...")
    reply = ScoutResult(session_id=msg.session_id, candidates=candidates)
    await ctx.send(sender, reply)


scout_agent.include(scout_proto)


if __name__ == "__main__":
    scout_agent.run()
