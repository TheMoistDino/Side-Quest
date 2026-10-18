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

class QuestCandidate(Model):
    id: str
    name: str
    lat: float
    lng: float
    estimated_admission: float
    estimated_dwell_minutes: int
    opening_hours: str = "10:00 AM - 9:00 PM"
    description: str = ""
    perk: str = ""


class ScoutQuery(Model):
    session_id: str
    query_area: str
    category: str
    max_admission: float


class ScoutResult(Model):
    session_id: str
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
