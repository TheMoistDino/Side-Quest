"""
planner.py: Core Quest Planner Logic for Quest Orchestrator.

Handles:
- Natural language extraction of constraints:
  * Temporal window (departure, return cutoff, duration in mins)
  * Fiscal limit (budget in USD)
  * Starting point / neighborhood
  * Vibe / activity category
- Feasibility calculations (temporal budget ΔT, fiscal budget ΔC)
- Multi-stop schedule synthesis with transit buffer, main dwell time, and opportunistic meal/snack stops
- RPG-themed "Sidequest Log" markdown generation
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class QuestConstraints(BaseModel):
    duration_minutes: int = Field(default=120, description="Available free time window in minutes")
    budget_usd: float = Field(default=30.0, description="Budget cap in USD")
    origin: str = Field(default="Westwood / UCLA", description="Starting neighborhood or landmark")
    vibe: str = Field(default="adventure", description="Requested vibe or activity type")
    departure_time: Optional[str] = Field(default=None, description="Preferred departure time string")
    return_cutoff: Optional[str] = Field(default=None, description="Hard deadline to return")
    max_distance_miles: Optional[float] = Field(default=10.0, description="Max travel radius in miles")
    group_size: int = Field(default=1, description="Party size")
    user_lat: float = Field(default=34.0635, description="Starting latitude")
    user_lng: float = Field(default=-118.4455, description="Starting longitude")


class ItineraryStop(BaseModel):
    title: str
    category: str
    dwell_minutes: int
    estimated_cost: float
    description: str
    perk: str


class QuestPlan(BaseModel):
    quest_title: str
    rank: str
    origin: str
    vibe: str
    total_time_minutes: int
    used_time_minutes: int
    slack_time_minutes: int
    total_budget_usd: float
    spent_budget_usd: float
    remaining_budget_usd: float
    transit_buffer_minutes: int
    stops: List[Dict[str, Any]]
    rewards: List[str]
    tactical_tips: List[str]


# Curated catalog of LA adventure nodes categorized by neighborhood and vibe
LA_QUEST_CATALOG: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
    "westwood": {
        "art": [
            {
                "name": "Hammer Museum Courtyard & Galleries",
                "dwell": 60,
                "cost": 0.0,
                "desc": "Inspect contemporary exhibits and decompress in the open-air courtyard.",
                "perk": "+20 Cultural Wisdom, Free Admission Perk",
            },
            {
                "name": "Fowler Museum Cultural Relics",
                "dwell": 45,
                "cost": 0.0,
                "desc": "Browse global archeology and indigenous art on the UCLA campus.",
                "perk": "+15 Ancient Lore",
            },
        ],
        "chill": [
            {
                "name": "UCLA Mathias Botanical Garden",
                "dwell": 50,
                "cost": 0.0,
                "desc": "Forest bath amidst 3,000+ species of tropical flora.",
                "perk": "+25 Mental Resilience, Stress Purge",
            },
            {
                "name": "Upside Down Coffee & Community Space",
                "dwell": 35,
                "cost": 6.5,
                "desc": "Non-profit specialty coffee bar and community gallery patio.",
                "perk": "+15 Social Morale, Community Insight",
            },
        ],
        "outdoors": [
            {
                "name": "UCLA Mathias Botanical Garden Canopy Walk",
                "dwell": 50,
                "cost": 0.0,
                "desc": "Scenic outdoor trail navigating native redwood groves and streams.",
                "perk": "+25 Botanical Lore, Stamina Restore",
            },
        ],
        "food": [
            {
                "name": "Diddy Riese Custom Cookie Sandwich",
                "dwell": 25,
                "cost": 4.5,
                "desc": "Acquire freshly baked warm cookies with premium ice cream center.",
                "perk": "+15 Sugar Rush, +10 Morale",
            },
            {
                "name": "Sawtelle Japantown Ramen Expedition",
                "dwell": 55,
                "cost": 18.0,
                "desc": "Venture down Olympic to slurp rich tonkotsu broth at Tsujita Annex.",
                "perk": "+30 Satiety, Umami Surge",
            },
        ],
        "tech": [
            {
                "name": "Boelter Hall 3420 (Birthplace of the Internet)",
                "dwell": 35,
                "cost": 0.0,
                "desc": "Pay homage to Interface Message Processor #1 where the first ARPANET message 'LO' was sent.",
                "perk": "+50 Hacker Prestige, ARPANET Genesis Artifact",
            }
        ],
        "arcade": [
            {
                "name": "Ackerman Union Game Zone & Arcade",
                "dwell": 50,
                "cost": 8.0,
                "desc": "Campus gaming lounge with DDR, pool tables, pinball, and fighting games.",
                "perk": "+25 Rhythm Agility, Bruin High Score",
            },
            {
                "name": "Dave & Buster's West LA Arcade",
                "dwell": 60,
                "cost": 20.0,
                "desc": "High-tech arcade with racing pods, VR games, and air hockey.",
                "perk": "+35 High Score Chaser",
            },
        ],
    },
    "santa monica": {
        "outdoors": [
            {
                "name": "Ocean View Park Bluff Trail",
                "dwell": 50,
                "cost": 0.0,
                "desc": "Coastal bluff trail overlooking the Pacific Ocean with sea breeze and vista.",
                "perk": "+30 Ocean Clarity, Cardiovascular Boost",
            },
            {
                "name": "Santa Monica Stairs & Ocean Promenade",
                "dwell": 45,
                "cost": 0.0,
                "desc": "Famous steep wooden canyon outdoor workout stairs with panoramic ocean views.",
                "perk": "+35 Athletic Stamina, Leg Power Buff",
            },
            {
                "name": "Palisades Park Coastal Bluffs Trail",
                "dwell": 55,
                "cost": 0.0,
                "desc": "1.6-mile palm-lined blufftop walking trail with dramatic ocean panoramas.",
                "perk": "+25 Coastal Vigor",
            },
        ],
        "chill": [
            {
                "name": "Ocean View Park Bluff Walk",
                "dwell": 50,
                "cost": 0.0,
                "desc": "Stroll the Pacific Palisades cliffs catching sea breeze and coastal sunset.",
                "perk": "+20 Vitality, Ocean Clarity",
            },
            {
                "name": "Dogtown Skate Park & Promenade",
                "dwell": 45,
                "cost": 0.0,
                "desc": "Watch locals carve concrete bowls at the historic birthplace of skate culture.",
                "perk": "+15 Dexterity",
            },
        ],
        "art": [
            {
                "name": "Bergamot Station Arts Center",
                "dwell": 65,
                "cost": 0.0,
                "desc": "Explore 20+ independent contemporary art galleries in former train depot sheds.",
                "perk": "+30 Aesthetic Perception",
            }
        ],
        "food": [
            {
                "name": "Bay Cities Italian Deli Godmother",
                "dwell": 35,
                "cost": 14.5,
                "desc": "Secure a crusty Italian roll loaded with Genoa salami, mortadella, capicola and spicy peppers.",
                "perk": "+40 Stamina Reserve",
            },
            {
                "name": "Sidecar Doughnuts Huckleberry Glaze",
                "dwell": 20,
                "cost": 6.0,
                "desc": "Bite into a warm sourdough donut fried fresh every hour.",
                "perk": "+10 Swiftness",
            },
        ],
        "arcade": [
            {
                "name": "Playland Arcade on Santa Monica Pier",
                "dwell": 50,
                "cost": 15.0,
                "desc": "Historic beachfront pier arcade featuring classic skeeball, pinball, and air hockey.",
                "perk": "+30 Pier Nostalgia Buff",
            },
            {
                "name": "Pacific Park Boardwalk Midway Games",
                "dwell": 40,
                "cost": 12.0,
                "desc": "Classic oceanfront midway games including ring toss and balloon pop.",
                "perk": "+20 Dexterity Buff",
            },
        ],
    },
    "koreatown": {
        "chill": [
            {
                "name": "Koreatown Pavilion Garden (Da Wool Jung)",
                "dwell": 40,
                "cost": 0.0,
                "desc": "Traditional open-air pavilion built by South Korean artisans showcasing Joseon architecture.",
                "perk": "+25 Cultural Harmony, Zen Calm",
            },
            {
                "name": "Chapman Plaza Historic Walk",
                "dwell": 35,
                "cost": 0.0,
                "desc": "Admire the 1929 Spanish Colonial Revival castle courtyard and neon architecture.",
                "perk": "+15 Architectural Vision",
            },
            {
                "name": "Wi Spa Rooftop & Salt Sauna",
                "dwell": 90,
                "cost": 30.0,
                "desc": "Immerse in mineral baths and heated jade rooms in a 24hr sanctuary.",
                "perk": "+50 Regeneration, Deep Cleansing Aura",
            },
        ],
        "food": [
            {
                "name": "Sun Nong Dan Midnight Galbi Jjim",
                "dwell": 60,
                "cost": 28.0,
                "desc": "Feast on braised beef short ribs torched with melted cheese table-side.",
                "perk": "+60 Strength, Legendary Feast",
            },
            {
                "name": "K-Town Street Cart Tteokbokki & Hotteok",
                "dwell": 30,
                "cost": 10.0,
                "desc": "Quick snack of fiery rice cakes and brown sugar stuffed pancakes.",
                "perk": "+20 Fire Affinity, Quick Fuel",
            },
        ],
        "arcade": [
            {
                "name": "Shatto 39 Neon Bowling & Arcade",
                "dwell": 50,
                "cost": 15.0,
                "desc": "Retro bowling lanes with retro coin-op arcade cabinets and neon glow.",
                "perk": "+25 Precision, Neon Reflexes",
            }
        ],
    },
    "downtown la": {
        "art": [
            {
                "name": "The Broad Infinity Mirror & Pop Art",
                "dwell": 75,
                "cost": 0.0,
                "desc": "Walk through Yayoi Kusama's celestial reflections and iconic Warhol/Basquiat canvases.",
                "perk": "+35 Cosmic Perspective, Visionary Sight",
            },
            {
                "name": "The Last Bookstore Labyrinth",
                "dwell": 45,
                "cost": 5.0,
                "desc": "Wander through spiraling book tunnels and hidden record vaults.",
                "perk": "+20 Bibliophile Intellect",
            },
        ],
        "food": [
            {
                "name": "Grand Central Market Food Odyssey",
                "dwell": 45,
                "cost": 16.0,
                "desc": "Grab tacos from Villa Moreliana or an egg salad brioche at Eggslut.",
                "perk": "+25 Gastronomy Insight",
            },
            {
                "name": "Little Tokyo Daikokuya Gyoza Bar",
                "dwell": 40,
                "cost": 14.0,
                "desc": "Crispy pan-fried pork dumplings under hanging Japanese paper lanterns.",
                "perk": "+20 Satiety",
            },
        ],
        "chill": [
            {
                "name": "Angels Flight Funicular & Bunker Hill",
                "dwell": 30,
                "cost": 1.0,
                "desc": "Ride the 1901 wooden funicular railway between Hill and Olive Streets.",
                "perk": "+10 Nostalgia Charm",
            }
        ],
        "arcade": [
            {
                "name": "EightyTwo Vintage Arcade & Pinball",
                "dwell": 60,
                "cost": 10.0,
                "desc": "Legendary vintage arcade featuring 55+ classic arcade cabinets and pinball.",
                "perk": "+40 Nostalgia Mastery",
            },
            {
                "name": "Two Bit Circus Micro-Amusement Park",
                "dwell": 75,
                "cost": 25.0,
                "desc": "High-tech indie arcade with VR arenas and custom carnival games.",
                "perk": "+45 Techno-Illusionist",
            },
        ],
    },
}

OPPORTUNISTIC_SNACKS: List[Dict[str, Any]] = [
    {
        "name": "Boba Time Milk Tea with Herbal Jelly",
        "dwell": 20,
        "cost": 6.5,
        "desc": "Cool, caffeinated elixir to replenish stamina on the go.",
        "perk": "+10 Hydration, Sugar Boost",
    },
    {
        "name": "Al Pastor Taco Stand (Street Cart)",
        "dwell": 20,
        "cost": 7.0,
        "desc": "Two double-corn tortilla tacos carved straight from the spinning trompo with pineapple.",
        "perk": "+20 Energy Replenishment",
    },
    {
        "name": "Artisanal Matcha Latte Drop",
        "dwell": 20,
        "cost": 6.0,
        "desc": "Stone-ground ceremonial Uji matcha whisked with oat milk.",
        "perk": "+15 Focus, Zen State",
    },
    {
        "name": "Warm Churro with Dulce de Leche",
        "dwell": 15,
        "cost": 4.5,
        "desc": "Crispy cinnamon-sugar pastry fresh from the fryer.",
        "perk": "+10 Instant Joy",
    },
]


def parse_time_str(time_str: str) -> Optional[datetime]:
    """Parse time string like '2:00 PM', '14:30', '2pm', '4:30 PM' into today's datetime."""
    clean = time_str.strip().upper()
    if not clean:
        return None
    clean = re.sub(r"(\d+)(AM|PM)", r"\1 \2", clean)
    if ":" not in clean and ("AM" in clean or "PM" in clean):
        clean = re.sub(r"(\d+)\s*(AM|PM)", r"\1:00 \2", clean)
    for fmt in ["%I:%M %p", "%H:%M", "%I %p"]:
        try:
            parsed = datetime.strptime(clean, fmt)
            now = datetime.now()
            return now.replace(hour=parsed.hour, minute=parsed.minute, second=0, microsecond=0)
        except ValueError:
            pass
    return None


def extract_constraints(user_text: str) -> QuestConstraints:
    """Extract temporal, financial, and spatial constraints using robust regex & heuristics."""
    text_lower = user_text.lower()
    constraints = QuestConstraints()

    # 1. Temporal Window / Duration extraction
    # Matches: "2 hours", "90 minutes", "1.5 hours", "3 hrs", "45 mins"
    duration_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)\b", text_lower)
    if duration_match:
        hours = float(duration_match.group(1))
        constraints.duration_minutes = int(hours * 60)
    else:
        min_match = re.search(r"(\d+)\s*(?:minutes?|mins?|m)\b", text_lower)
        if min_match:
            constraints.duration_minutes = int(min_match.group(1))

    # Departure time extraction: "it is 2:00 PM", "starting at 2pm", "departs at 14:00"
    dep_match = re.search(
        r"\b(?:it is|it's|start(?:ing)?(?: at)?|depart(?:ing|s)?(?: at)?)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        text_lower,
    )
    if dep_match:
        constraints.departure_time = dep_match.group(1)

    # Matches window ranges: "from 2pm to 5pm", "between 14:00 and 17:30"
    window_match = re.search(
        r"(?:from|between)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\s*(?:to|and|-)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)",
        text_lower,
    )
    if window_match:
        constraints.departure_time = window_match.group(1)
        constraints.return_cutoff = window_match.group(2)

    # Hard return cutoff: "back home in Santa Monica by 4:30 pm", "back by 6pm", "return before 8:30 pm"
    cutoff_match = re.search(
        r"(?:back(?: home)?(?:\s+(?:in|to)\s+[a-zA-Z\s]+)?\s+by|return (?:by|before)|until|before)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b",
        text_lower,
    )
    if cutoff_match:
        constraints.return_cutoff = cutoff_match.group(1)

    # Calculate duration if departure and return cutoff are both identified
    if constraints.departure_time and constraints.return_cutoff:
        dt_dep = parse_time_str(constraints.departure_time)
        dt_ret = parse_time_str(constraints.return_cutoff)
        if dt_dep and dt_ret:
            if dt_ret < dt_dep:
                dt_ret += timedelta(days=1)
            delta_mins = int((dt_ret - dt_dep).total_seconds() / 60)
            if delta_mins > 0:
                constraints.duration_minutes = delta_mins

    # 2. Fiscal Budget extraction
    # Priority A: Explicit numerical budget (e.g., "$35", "$ 50.00", "20 dollars", "budget of $45", "budget: 50")
    budget_match = re.search(r"\$\s*(\d+(?:\.\d{1,2})?)", text_lower)
    if not budget_match:
        budget_match = re.search(r"(\d+(?:\.\d{1,2})?)\s*(?:dollars|bucks|usd)\b", text_lower)
    if not budget_match:
        budget_match = re.search(r"\bbudget(?:\s*is|\s*of|\s*:)?\s*\$?\s*(\d+(?:\.\d{1,2})?)\b", text_lower)

    if budget_match:
        constraints.budget_usd = float(budget_match.group(1))
    elif "$0" in text_lower or "zero dollars" in text_lower or "no money" in text_lower or "zero budget" in text_lower:
        constraints.budget_usd = 0.0
    elif re.search(r"\bfree\b(?!\s*(?:time|hours?|hrs?|minutes?|mins?|for|window|recon))", text_lower):
        constraints.budget_usd = 0.0

    # 3. Starting Neighborhood extraction
    neighborhoods = {
        "westwood": "Westwood / UCLA",
        "ucla": "Westwood / UCLA",
        "santa monica": "Santa Monica / Ocean",
        "venice": "Venice Beach",
        "koreatown": "Koreatown",
        "ktown": "Koreatown",
        "downtown": "Downtown LA (DTLA)",
        "dtla": "Downtown LA (DTLA)",
        "sawtelle": "Sawtelle Japantown",
        "hollywood": "Hollywood",
        "silver lake": "Silver Lake",
        "culver city": "Culver City",
        "pasadena": "Pasadena",
    }
    for key, name in neighborhoods.items():
        if key in text_lower:
            constraints.origin = name
            break

    # 4. Vibe / Activity extraction
    # Outdoors / Adventure / Trails takes priority when explicitly requested (e.g. "outdoor adventure quest")
    if re.search(r"\b(?:outdoors?|adventure|trails?|hike|hiking|trek|park|beach|stairs|views?|viewpoint|active|nature|bluff|coast|coastal)\b", text_lower):
        constraints.vibe = "outdoors"
    elif re.search(r"\b(?:museum|museums|gallery|galleries|art|paintings?|exhibit|culture|sculpture)\b", text_lower):
        constraints.vibe = "art"
    elif re.search(r"\b(?:eat|eats|eating|snack|snacks|dinner|lunch|food|foodie|ramen|tacos|cookies?|bakery|coffee|cafe|dessert)\b", text_lower):
        constraints.vibe = "food"
    elif re.search(r"\b(?:tech|internet|hacker|cyber|boelter|code)\b", text_lower):
        constraints.vibe = "tech"
    elif re.search(r"\b(?:arcade|bowling|games?|gaming|retro)\b", text_lower):
        constraints.vibe = "arcade"
    elif re.search(r"\b(?:chill|zen|relax|relaxation|spa|peaceful|stroll)\b", text_lower):
        constraints.vibe = "chill"
    else:
        constraints.vibe = "chill"

    return constraints


def synthesize_quest(constraints: QuestConstraints) -> QuestPlan:
    """Synthesize multi-stop schedule with feasibility checks and opportunistic stops."""
    total_t = constraints.duration_minutes
    total_b = constraints.budget_usd

    # Determine region key
    origin_lower = constraints.origin.lower()
    if "santa monica" in origin_lower or "venice" in origin_lower:
        reg_key = "santa monica"
    elif "koreatown" in origin_lower or "ktown" in origin_lower:
        reg_key = "koreatown"
    elif "downtown" in origin_lower or "dtla" in origin_lower:
        reg_key = "downtown la"
    else:
        reg_key = "westwood"

    # Transit buffer estimation (roundtrip / intra-area transit)
    # Hyper-local trips take 15-25 min round trip transit buffer
    transit_buffer = 20 if total_t <= 90 else 30

    effective_time_avail = max(10, total_t - transit_buffer)
    remaining_budget = total_b

    # Select Primary Quest based on vibe and region
    region_catalog = LA_QUEST_CATALOG.get(reg_key, LA_QUEST_CATALOG["westwood"])
    vibe_candidates = region_catalog.get(constraints.vibe, [])
    if not vibe_candidates and constraints.vibe in ["outdoors", "adventure", "trails"]:
        vibe_candidates = region_catalog.get("outdoors", [])
    if not vibe_candidates:
        # Fallback to any category in the region
        for cat in region_catalog.values():
            vibe_candidates.extend(cat)

    # Pick best candidate that fits BOTH budget and time constraints
    primary_candidate = None
    for cand in vibe_candidates:
        if cand["cost"] <= remaining_budget and cand["dwell"] <= effective_time_avail:
            primary_candidate = cand
            break

    # If no exact match within vibe, check any candidate across all categories in the region
    if not primary_candidate:
        all_regional = [c for cat in region_catalog.values() for c in cat]
        for cand in all_regional:
            if cand["cost"] <= remaining_budget and cand["dwell"] <= effective_time_avail:
                primary_candidate = cand
                break

    # Fallback to a zero-cost local walking quest if budget is $0 or no candidate fit
    if not primary_candidate:
        primary_candidate = {
            "name": f"Urban Exploration Walk around {constraints.origin}",
            "dwell": min(45, effective_time_avail),
            "cost": 0.0,
            "desc": f"Chart uncharted architectural gems and open courtyards in {constraints.origin}.",
            "perk": "+15 Cartographer EXP, Zero Cost Mastery",
        }

    stops: List[Dict[str, Any]] = [
        {
            "step": 1,
            "type": "Primary Objective",
            "name": primary_candidate["name"],
            "dwell_mins": primary_candidate["dwell"],
            "cost_usd": primary_candidate["cost"],
            "description": primary_candidate["desc"],
            "perk": primary_candidate["perk"],
        }
    ]

    time_used = transit_buffer + primary_candidate["dwell"]
    remaining_budget -= primary_candidate["cost"]
    slack_time = total_t - time_used

    # Opportunistic Snack / Meal Integration:
    # Triggered if slack time >= 30 mins AND funds permit (>= $5)
    opportunistic_added = False
    if slack_time >= 30 and remaining_budget >= 4.5:
        snack_candidates = [s for s in OPPORTUNISTIC_SNACKS if s["cost"] <= remaining_budget and s["dwell"] <= (slack_time - 10)]
        if snack_candidates:
            snack = snack_candidates[0]
            stops.append({
                "step": 2,
                "type": "Opportunistic Supply Drop (Bonus Objective)",
                "name": snack["name"],
                "dwell_mins": snack["dwell"],
                "cost_usd": snack["cost"],
                "description": snack["desc"],
                "perk": snack["perk"],
            })
            time_used += snack["dwell"]
            remaining_budget -= snack["cost"]
            slack_time = total_t - time_used
            opportunistic_added = True

    # Ranks and Titles
    if total_t >= 180:
        rank = "RANK S - EPIC CAMPAIGN"
    elif total_t >= 120:
        rank = "RANK A - VETERAN ADVENTURE"
    elif total_t >= 60:
        rank = "RANK B - RAPID RECON"
    else:
        rank = "RANK C - MICRO PATROL"

    vibe_titles = {
        "art": "Aesthetic Reverie",
        "chill": "Zen Sanctuary Protocol",
        "food": "Gastronomic Expedition",
        "tech": "Cybernetic Relic Hunt",
        "arcade": "Neon Drift Run",
    }
    quest_title = f"Operation: {vibe_titles.get(constraints.vibe, 'Urban Odysseys')} in {constraints.origin}"

    rewards = [
        f"💰 Fiscal Efficiency: Spent ${total_b - remaining_budget:.2f} of ${total_b:.2f} limit (Reserves: ${remaining_budget:.2f})",
        f"⏳ Time Reserve: {slack_time} mins buffer remaining for unexpected encounters",
    ]
    for s in stops:
        rewards.append(f"✨ Reward: {s['perk']}")

    tactical_tips = [
        f"Transit allowance: ~{transit_buffer} mins allocated for transit/parking buffers.",
        "Keep student/hacker ID handy for surprise discounts at LA cultural checkpoints.",
        "Always keep a water bottle equipped in off-hand slot to withstand SoCal sunshine.",
    ]
    if constraints.return_cutoff:
        tactical_tips.append(f"Hard Return Deadline: Scheduled completion calibrated for return by {constraints.return_cutoff}.")

    return QuestPlan(
        quest_title=quest_title,
        rank=rank,
        origin=constraints.origin,
        vibe=constraints.vibe,
        total_time_minutes=total_t,
        used_time_minutes=time_used,
        slack_time_minutes=slack_time,
        total_budget_usd=total_b,
        spent_budget_usd=round(total_b - remaining_budget, 2),
        remaining_budget_usd=round(remaining_budget, 2),
        transit_buffer_minutes=transit_buffer,
        stops=stops,
        rewards=rewards,
        tactical_tips=tactical_tips,
    )


def render_rpg_log(plan: QuestPlan, base_time: Optional[datetime] = None) -> str:
    """Format QuestPlan into an RPG-styled markdown log for ASI:One chat."""
    if not base_time:
        base_time = datetime.now()

    current_t = base_time
    timeline_lines = []

    # Transit leg to first objective
    half_transit = plan.transit_buffer_minutes // 2
    t_depart = current_t.strftime("%H:%M")
    current_t += timedelta(minutes=half_transit)
    t_arrive = current_t.strftime("%H:%M")
    timeline_lines.append(f"- **[{t_depart} → {t_arrive}]** 🧭 *Fast Travel Leg 1*: Ingress from `{plan.origin}` ({half_transit}m transit buffer)")

    for idx, stop in enumerate(plan.stops):
        dwell = stop["dwell_mins"]
        t_start = current_t.strftime("%H:%M")
        current_t += timedelta(minutes=dwell)
        t_end = current_t.strftime("%H:%M")
        cost_tag = f"${stop['cost_usd']:.2f}" if stop['cost_usd'] > 0 else "FREE"
        timeline_lines.append(
            f"- **[{t_start} → {t_end}]** 📍 **{stop['type']}**: `{stop['name']}` ({dwell}m dwell | Cost: {cost_tag})\n"
            f"  > *Intel*: {stop['description']}\n"
            f"  > *Equipped Perk*: `{stop['perk']}`"
        )
        if idx < len(plan.stops) - 1:
            current_t += timedelta(minutes=5)
            timeline_lines.append(f"  *↳ 5m tactical stroll / queue leeway*")

    # Ingress back home
    t_return_start = current_t.strftime("%H:%M")
    current_t += timedelta(minutes=half_transit)
    t_return_end = current_t.strftime("%H:%M")
    timeline_lines.append(f"- **[{t_return_start} → {t_return_end}]** 🏠 *Fast Travel Leg 2*: Exgress & Return Base ({half_transit}m buffer)")

    timeline_str = "\n".join(timeline_lines)
    rewards_str = "\n".join(f"- {r}" for r in plan.rewards)
    tips_str = "\n".join(f"- {tip}" for tip in plan.tactical_tips)

    log_markdown = f"""
🎮 **[SIDEQUEST LOG]** `{plan.quest_title}`
⚔️ **Rank**: `{plan.rank}` | 📍 **Origin**: `{plan.origin}` | 🎭 **Vibe**: `{plan.vibe.upper()}`

---
### 📊 Resource Budget & Feasibility
- ⏱️ **Temporal Budget ($\\Delta T$)**: `{plan.used_time_minutes} min` used / `{plan.total_time_minutes} min` allotted (🛡️ Slack: `{plan.slack_time_minutes} min`)
- 💵 **Fiscal Budget ($\\Delta C$)**: `${plan.spent_budget_usd:.2f}` spent / `${plan.total_budget_usd:.2f}` cap (🪙 Remaining: `${plan.remaining_budget_usd:.2f}`)

---
### 🗺️ Micro-Itinerary & Waypoints
{timeline_str}

---
### 🏆 Loot & Character Buffs
{rewards_str}

---
### 💡 Tactical Recon Tips
{tips_str}

*Quest generated autonomously by Quest Orchestrator (@quest-orchestrator) on Fetch.ai ACP.*
""".strip()

    return log_markdown


def render_multiagent_rpg_log(
    constraints: QuestConstraints,
    candidate: Any,  # QuestCandidate
    chosen_transit: Any,  # TransitOption
    all_transit_options: List[Any],  # List[TransitOption]
    meal_res: Any,  # MealResult
    base_time: Optional[datetime] = None,
) -> str:
    """Format multi-agent synthesized itinerary into an RPG-styled markdown log."""
    if not base_time:
        base_time = datetime.now()

    total_time = constraints.duration_minutes
    total_budget = constraints.budget_usd

    # Calculate time and cost
    one_way_transit_mins = chosen_transit.duration_minutes
    roundtrip_transit_mins = 2 * one_way_transit_mins
    transit_cost = chosen_transit.estimated_cost
    roundtrip_transit_cost = 2 * transit_cost if chosen_transit.mode != "driving" else transit_cost

    dwell_mins = candidate.estimated_dwell_minutes
    admission_cost = candidate.estimated_admission

    time_used = roundtrip_transit_mins + dwell_mins
    cost_spent = roundtrip_transit_cost + admission_cost

    meal_dwell = 0
    meal_cost = 0.0
    if meal_res and meal_res.recommended and meal_res.spot_name:
        meal_dwell = meal_res.dwell_mins
        meal_cost = meal_res.estimated_cost
        time_used += meal_dwell
        cost_spent += meal_cost

    slack_time = max(0, total_time - time_used)
    remaining_budget = max(0.0, total_budget - cost_spent)

    # Determine Rank
    if total_time >= 180:
        rank = "RANK S - EPIC CAMPAIGN"
    elif total_time >= 120:
        rank = "RANK A - VETERAN ADVENTURE"
    elif total_time >= 60:
        rank = "RANK B - RAPID RECON"
    else:
        rank = "RANK C - MICRO PATROL"

    # Timeline construction
    current_t = base_time
    timeline_lines = []

    # Ingress Leg
    t_start = current_t.strftime("%H:%M")
    current_t += timedelta(minutes=one_way_transit_mins)
    t_arr = current_t.strftime("%H:%M")
    cost_str = f"${transit_cost:.2f}" if transit_cost > 0 else "FREE"
    timeline_lines.append(
        f"- **[{t_start} → {t_arr}]** 🧭 *Ingress Leg*: `{chosen_transit.mode.upper()}` from `{constraints.origin}` ({one_way_transit_mins}m | Cost: {cost_str})\n"
        f"  > *Mobility Intel*: {chosen_transit.details}"
    )

    # Primary Objective Leg
    t_obj_start = current_t.strftime("%H:%M")
    current_t += timedelta(minutes=dwell_mins)
    t_obj_end = current_t.strftime("%H:%M")
    admit_str = f"${admission_cost:.2f}" if admission_cost > 0 else "FREE"
    rev_intel = f"\n  > *Review Consensus*: {candidate.review_summary}" if getattr(candidate, "review_summary", None) else ""
    timeline_lines.append(
        f"- **[{t_obj_start} → {t_obj_end}]** 📍 **Primary Quest Waypoint**: `{candidate.name}` ({dwell_mins}m dwell | Admission: {admit_str})\n"
        f"  > *Intel*: {candidate.description}\n"
        f"  > *GPS Coordinates*: `{candidate.lat:.4f}, {candidate.lng:.4f}` | *Hours*: `{candidate.opening_hours}`\n"
        f"  > *Equipped Perk*: `{candidate.perk}`{rev_intel}"
    )

    # Opportunistic Food Stop Leg
    if meal_res and meal_res.recommended and meal_res.spot_name:
        current_t += timedelta(minutes=5)
        timeline_lines.append("  *↳ 5m tactical stroll / queue leeway*")
        t_meal_start = current_t.strftime("%H:%M")
        current_t += timedelta(minutes=meal_dwell)
        t_meal_end = current_t.strftime("%H:%M")
        timeline_lines.append(
            f"- **[{t_meal_start} → {t_meal_end}]** 🍔 **Opportunistic Supply Drop**: `{meal_res.spot_name}` ({meal_dwell}m dwell | Cost: ${meal_cost:.2f})\n"
            f"  > *Budget Agent Reasoning*: {meal_res.reasoning}\n"
            f"  > *Gastronomy Buff*: `{meal_res.perk or '+15 Satiety, Morale Boost'}`"
        )

    # Exgress Return Leg
    t_ret_start = current_t.strftime("%H:%M")
    current_t += timedelta(minutes=one_way_transit_mins)
    t_ret_end = current_t.strftime("%H:%M")
    timeline_lines.append(
        f"- **[{t_ret_start} → {t_ret_end}]** 🏠 *Exgress Leg*: Return Base via `{chosen_transit.mode.upper()}` ({one_way_transit_mins}m)"
    )

    timeline_str = "\n".join(timeline_lines)

    # Multi-modal alternatives
    alt_lines = []
    for opt in all_transit_options:
        cost_tag = f"${opt.estimated_cost:.2f}" if opt.estimated_cost > 0 else "FREE"
        star = " ★ (Selected)" if opt.mode == chosen_transit.mode else ""
        alt_lines.append(f"- **{opt.mode.capitalize()}**: `{opt.duration_minutes} min` | `{cost_tag}` — {opt.details}{star}")
    alt_str = "\n".join(alt_lines)

    # Rewards
    rewards = [
        f"💰 Fiscal Efficiency: Spent ${cost_spent:.2f} of ${total_budget:.2f} cap (Reserves: ${remaining_budget:.2f})",
        f"⏳ Time Reserve: {slack_time} min slack buffer remaining",
        f"✨ Scout Discovery Reward: `{candidate.perk}`",
    ]
    if meal_res and meal_res.recommended and meal_res.perk:
        rewards.append(f"✨ Culinary Reward: `{meal_res.perk}`")
    rewards_str = "\n".join(f"- {r}" for r in rewards)

    # Tactical Tips
    tips = [
        f"Multi-Agent Network: ScoutAgent located POI, TransitAgent routed {chosen_transit.mode}, BudgetAgent allocated dining.",
        "Keep student/hacker ID handy for surprise discounts at cultural checkpoints.",
        "Equip a water bottle in off-hand slot to withstand SoCal sunshine.",
    ]
    if constraints.return_cutoff:
        tips.append(f"Hard Return Deadline: Scheduled completion calibrated for return by {constraints.return_cutoff}.")
    tips_str = "\n".join(f"- {tip}" for tip in tips)

    title = f"Operation: Urban Odyssey in {constraints.origin}"

    return f"""
🎮 **[SIDEQUEST LOG]** `{title}`
⚔️ **Rank**: `{rank}` | 📍 **Origin**: `{constraints.origin}` | 🎭 **Vibe**: `{constraints.vibe.upper()}`

---
### 📊 Resource Budget & Feasibility
- ⏱️ **Temporal Budget ($\\Delta T$)**: `{time_used} min` used / `{total_time} min` allotted (🛡️ Slack: `{slack_time} min`)
- 💵 **Fiscal Budget ($\\Delta C$)**: `${cost_spent:.2f}` spent / `${total_budget:.2f}` cap (🪙 Remaining: `${remaining_budget:.2f}`)

---
### 🗺️ Micro-Itinerary & Waypoints
{timeline_str}

---
### 🚦 Multi-Modal Transit Intelligence (TransitAgent)
{alt_str}

---
### 🏆 Loot & Character Buffs
{rewards_str}

---
### 💡 Tactical Recon Tips
{tips_str}

*Synthesized autonomously by Quest Orchestrator Bureau with Scout, Transit, and Budget subagents.*
""".strip()

