"""
schemas.py: Shared typed Pydantic/uAgents Model schemas for multi-agent RPC.

Defines inter-agent communication models between:
- Quest Orchestrator (agent.py)
- Scout Agent (scout_agent.py)
- Transit & Mobility Agent (transit_agent.py)
- Budget & Meal Agent (budget_agent.py)
"""

from typing import List, Optional
from uagents import Model


# ==============================================================================
# Scout Agent Schemas
# ==============================================================================

class VerifiedReview(Model):
    author: str
    rating: float
    excerpt: str = ""
    source_platform: str = "Google Maps"  # e.g., "Yelp", "AllTrails", "Google Maps", "TripAdvisor"
    source_url: str = ""

    # Backwards-compatibility aliases
    text: str = ""
    source: str = ""

    def __init__(self, **data):
        # Synchronize text and excerpt
        if "excerpt" in data and not data.get("text"):
            data["text"] = str(data["excerpt"])
        elif "text" in data and not data.get("excerpt"):
            data["excerpt"] = str(data["text"])
        elif "snippet" in data:
            data["excerpt"] = str(data["snippet"])
            data["text"] = str(data["snippet"])

        # Synchronize source_platform and source
        if "source_platform" in data and not data.get("source"):
            data["source"] = str(data["source_platform"])
        elif "source" in data and not data.get("source_platform"):
            data["source_platform"] = str(data["source"])
        elif "sourceName" in data:
            data["source_platform"] = str(data["sourceName"])
            data["source"] = str(data["sourceName"])

        super().__init__(**data)


class QuestCandidate(Model):
    id: str
    name: str
    address: str = ""
    lat: float
    lng: float
    admission_cost: float = 0.0
    estimated_dwell_mins: int = 45
    verified_url: str = ""        # Must be an active, verified URL (tested status < 400)
    reviews: List[VerifiedReview] = []
    is_verified: bool = True

    # Backwards-compatibility fields and enriched metadata
    estimated_admission: float = 0.0
    estimated_dwell_minutes: int = 45
    source_url: str = ""
    opening_hours: str = "10:00 AM - 9:00 PM"
    description: str = ""
    perk: str = ""
    category: str = ""
    rating: float = 4.6
    review_count: int = 150
    review_summary: str = ""

    def __init__(self, **data):
        # Synchronize admission costs
        if "admission_cost" in data and "estimated_admission" not in data:
            data["estimated_admission"] = float(data["admission_cost"])
        elif "estimated_admission" in data and "admission_cost" not in data:
            data["admission_cost"] = float(data["estimated_admission"])

        # Synchronize dwell times
        if "estimated_dwell_mins" in data and "estimated_dwell_minutes" not in data:
            data["estimated_dwell_minutes"] = int(data["estimated_dwell_mins"])
        elif "estimated_dwell_minutes" in data and "estimated_dwell_mins" not in data:
            data["estimated_dwell_mins"] = int(data["estimated_dwell_minutes"])

        # Synchronize verified URLs
        if "verified_url" in data and "source_url" not in data:
            data["source_url"] = str(data["verified_url"])
        elif "source_url" in data and "verified_url" not in data:
            data["verified_url"] = str(data["source_url"])

        # Normalize reviews to VerifiedReview
        if "reviews" in data and isinstance(data["reviews"], list):
            norm_reviews = []
            for r in data["reviews"]:
                if isinstance(r, dict):
                    norm_reviews.append(
                        VerifiedReview(
                            author=r.get("author", "Verified Visitor"),
                            rating=float(r.get("rating", 5.0)),
                            excerpt=r.get("excerpt") or r.get("text") or r.get("snippet", ""),
                            source_platform=r.get("source_platform") or r.get("source") or r.get("sourceName", "Google Maps"),
                            source_url=r.get("source_url") or r.get("sourceUrl", ""),
                        )
                    )
                elif isinstance(r, VerifiedReview):
                    norm_reviews.append(r)
            data["reviews"] = norm_reviews

        super().__init__(**data)


class ScoutQuery(Model):
    session_id: str
    query_area: str
    category: str
    max_admission: float
    departure_time: Optional[str] = None
    return_cutoff: Optional[str] = None


class ScoutResult(Model):
    session_id: str
    candidates: List[QuestCandidate]


# ==============================================================================
# Specialized Scout Subagent Schemas (Ensemble Pattern)
# ==============================================================================

class DiningQuery(Model):
    session_id: str
    area: str
    cuisine: Optional[str] = None
    budget_max: float = 50.0
    departure_time: Optional[str] = None
    return_cutoff: Optional[str] = None


class TrailsQuery(Model):
    session_id: str
    area: str
    intensity: str = "moderate"
    time_window_mins: int = 90
    departure_time: Optional[str] = None
    return_cutoff: Optional[str] = None


class CultureQuery(Model):
    session_id: str
    area: str
    exhibition_type: Optional[str] = None
    admission_max: float = 30.0
    departure_time: Optional[str] = None
    return_cutoff: Optional[str] = None


class ScoutSubResult(Model):
    session_id: str
    subagent: str  # "dining", "trails", "culture"
    candidates: List[QuestCandidate]


# ==============================================================================
# Transit & Mobility Agent Schemas
# ==============================================================================

class TransitOption(Model):
    mode: str  # "walking", "transit", "driving", "rideshare"
    duration_minutes: int
    estimated_cost: float
    details: str = ""


class TransitQuery(Model):
    session_id: str
    candidate_id: str
    origin: str
    destination_lat: float
    destination_lng: float
    departure_time: str = ""


class TransitResult(Model):
    session_id: str
    candidate_id: str
    options: List[TransitOption]
    recommended_mode: str = "transit"


# ==============================================================================
# Budget & Meal Agent Schemas
# ==============================================================================

class MealQuery(Model):
    session_id: str
    available_budget: float
    available_slack_time: int
    cuisine_preference: Optional[str] = None


class MealResult(Model):
    session_id: str
    recommended: bool
    spot_name: Optional[str] = None
    estimated_cost: float = 0.0
    dwell_mins: int = 0
    reasoning: str = ""
    perk: Optional[str] = None
