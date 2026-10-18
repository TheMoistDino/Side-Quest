"""
agent.py: Quest Orchestrator Agent (Primary Dispatcher).

Coordinates three specialized subagents running in a unified Bureau:
1. Scout Agent (scout_agent.py): POI discovery & dwell estimation
2. Transit & Mobility Agent (transit_agent.py): Multi-modal routing & fares
3. Budget & Meal Agent (budget_agent.py): Opportunistic culinary checkpoints

Maintains external registration on port 8000 with public ngrok /submit endpoint
compliant with Fetch.ai Agent Chat Protocol (ACP) for ASI:One (asi1.ai).
"""

import os
import sys
import uuid
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from schemas import (
    ScoutQuery,
    ScoutResult,
    QuestCandidate,
    TransitQuery,
    TransitResult,
    TransitOption,
    MealQuery,
    MealResult,
)

from planner import (
    extract_constraints,
    synthesize_quest,
    render_rpg_log,
    render_multiagent_rpg_log,
    QuestConstraints,
)

from scout_agent import scout_agent
from transit_agent import transit_agent
from budget_agent import budget_agent

# Configuration
PORT = int(os.getenv("PORT", "8000"))
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "https://liqueur-customize-nearby.ngrok-free.dev/submit").strip()
AGENT_SEED = os.getenv("AGENT_SEED_PHRASE", "fitlens").strip()
AGENT_NAME = os.getenv("AGENT_NAME", "Quest Orchestrator").strip()

# Initialize primary Orchestrator Agent
agent = Agent(
    name=AGENT_NAME,
    port=PORT,
    seed=AGENT_SEED,
    endpoint=[AGENT_ENDPOINT],
    handle_messages_concurrently=True,
)


class SmartResolver:
    """Composite resolver: resolves local subagents and test harnesses locally, queries Almanac otherwise."""
    def __init__(self, fallback_resolver):
        self.fallback = fallback_resolver
        self.local_routes = {
            agent.address: f"http://127.0.0.1:{PORT}/submit",
            scout_agent.address: f"http://127.0.0.1:{PORT}/submit",
            transit_agent.address: f"http://127.0.0.1:{PORT}/submit",
            budget_agent.address: f"http://127.0.0.1:{PORT}/submit",
        }

    async def resolve(self, destination: str):
        if destination in self.local_routes:
            return destination, [self.local_routes[destination]]
        try:
            dest, endpoints = await self.fallback.resolve(destination)
            if endpoints:
                return dest, endpoints
        except Exception:
            pass
        # Fallback routing to local simulator client
        return destination, ["http://127.0.0.1:8001/submit"]


agent._resolver = SmartResolver(agent._resolver)
scout_agent._resolver = SmartResolver(scout_agent._resolver)
transit_agent._resolver = SmartResolver(transit_agent._resolver)
budget_agent._resolver = SmartResolver(budget_agent._resolver)

# Instantiate Fetch.ai Agent Chat Protocol specification
chat_proto = Protocol(spec=chat_protocol_spec)

# Session tracking for multi-agent delegation pipeline
class QuestSession:
    def __init__(self, session_id: str, user_sender: str, constraints: QuestConstraints):
        self.session_id = session_id
        self.user_sender = user_sender
        self.constraints = constraints
        self.start_time = datetime.now()
        self.candidate: Optional[QuestCandidate] = None
        self.transit_options: list[TransitOption] = []
        self.chosen_transit: Optional[TransitOption] = None
        self.meal_result: Optional[MealResult] = None
        self.pipeline_complete = asyncio.Event()


active_sessions: Dict[str, QuestSession] = {}


@agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info("=" * 65)
    ctx.logger.info(f"🎮 {AGENT_NAME} ONLINE (Multi-Agent Bureau Active)")
    ctx.logger.info(f"📌 Orchestrator Address : {agent.address}")
    ctx.logger.info(f"🔭 Scout Agent Address  : {scout_agent.address}")
    ctx.logger.info(f"🚦 Transit Agent Address: {transit_agent.address}")
    ctx.logger.info(f"🍔 Budget Agent Address : {budget_agent.address}")
    ctx.logger.info(f"🌐 Public Webhook       : {AGENT_ENDPOINT}")
    ctx.logger.info(f"🔌 Local Port           : {PORT}")
    ctx.logger.info(f"💬 Protocol             : Fetch.ai Agent Chat Protocol (ACP)")
    ctx.logger.info("Ready for ASI:One multi-agent sidequest delegation!")
    ctx.logger.info("=" * 65)


# ==============================================================================
# ASI:One Chat Message Handling & Multi-Agent Orchestration
# ==============================================================================

@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    ctx.logger.info(f"📨 Incoming ChatMessage from {sender} (msg_id: {msg.msg_id})")

    # 1. Immediate ACP Delivery Acknowledgement
    try:
        ack = ChatAcknowledgement(acknowledged_msg_id=msg.msg_id)
        await ctx.send(sender, ack)
        ctx.logger.info(f"✅ Dispatched ChatAcknowledgement to {sender}")
    except Exception as e:
        ctx.logger.warning(f"Could not send acknowledgement: {e}")

    # 2. Extract plain text query
    incoming_query = ""
    if hasattr(msg, "text") and callable(msg.text):
        incoming_query = msg.text()
    elif hasattr(msg, "content"):
        for item in msg.content:
            if isinstance(item, TextContent):
                incoming_query += item.text + " "
            elif hasattr(item, "text"):
                incoming_query += str(item.text) + " "
            elif isinstance(item, str):
                incoming_query += item + " "

    incoming_query = incoming_query.strip()
    if not incoming_query:
        incoming_query = "2 hours free, $30 budget near Westwood for art or chill"

    ctx.logger.info(f"🔍 Analyzing user request: '{incoming_query}'")

    # 3. Parse constraints
    constraints = extract_constraints(incoming_query)
    session_id = str(uuid.uuid4())[:8]
    session = QuestSession(session_id=session_id, user_sender=sender, constraints=constraints)
    active_sessions[session_id] = session

    ctx.logger.info(
        f"🚀 Initiating Multi-Agent Pipeline [Session {session_id}]: "
        f"Area='{constraints.origin}', Category='{constraints.vibe}', "
        f"Duration={constraints.duration_minutes}m, Budget=${constraints.budget_usd:.2f}"
    )

    # 4. Step 1: Query Scout Agent
    scout_query = ScoutQuery(
        session_id=session_id,
        query_area=constraints.origin,
        category=constraints.vibe,
        max_admission=constraints.budget_usd,
    )
    await ctx.send(scout_agent.address, scout_query)

    # 5. Await pipeline completion with resilient timeout fallback
    try:
        await asyncio.wait_for(session.pipeline_complete.wait(), timeout=6.0)
        # Synthesize final itinerary using multi-agent output
        response_text = render_multiagent_rpg_log(
            constraints=session.constraints,
            candidate=session.candidate,
            chosen_transit=session.chosen_transit,
            all_transit_options=session.transit_options,
            meal_res=session.meal_result,
        )
        ctx.logger.info(f"✨ Multi-agent pipeline succeeded for session {session_id}!")
    except asyncio.TimeoutError:
        ctx.logger.warning(f"⚠️ Multi-agent pipeline timed out for session {session_id}. Employing deterministic fallback.")
        plan = synthesize_quest(constraints)
        response_text = render_rpg_log(plan)
    except Exception as err:
        ctx.logger.error(f"Error in multi-agent pipeline: {err}", exc_info=True)
        plan = synthesize_quest(constraints)
        response_text = render_rpg_log(plan)
    finally:
        active_sessions.pop(session_id, None)

    # 6. Dispatch ACP ChatMessage response back to user
    try:
        reply_msg = ChatMessage(content=[TextContent(type="text", text=response_text)])
        await ctx.send(sender, reply_msg)
        ctx.logger.info(f"🚀 Dispatched Sidequest Log to {sender} ({len(response_text)} chars)")
    except Exception as err:
        ctx.logger.error(f"Failed to dispatch ChatMessage reply: {err}", exc_info=True)


@chat_proto.on_message(ChatAcknowledgement)
async def handle_acknowledgement(ctx: Context, sender: str, msg: ChatAcknowledgement):
    ctx.logger.info(f"📬 Delivery confirmed by {sender} (acknowledged: {msg.acknowledged_msg_id})")


# ==============================================================================
# Inter-Agent RPC Handlers (Orchestrator Pipeline)
# ==============================================================================

orchestrator_proto = Protocol(name="OrchestratorPipelineProtocol", version="1.0.0")


@orchestrator_proto.on_message(ScoutResult)
async def handle_scout_result(ctx: Context, sender: str, msg: ScoutResult):
    session = active_sessions.get(msg.session_id)
    if not session:
        return

    ctx.logger.info(f"🔭 [Step 1 Received] ScoutAgent returned {len(msg.candidates)} candidates for session {msg.session_id}")
    
    # Pick top candidate
    candidate = msg.candidates[0] if msg.candidates else QuestCandidate(
        id="default-poi",
        name=f"Historic Walk around {session.constraints.origin}",
        lat=34.0689,
        lng=-118.4452,
        estimated_admission=0.0,
        estimated_dwell_minutes=45,
        opening_hours="Open 24/7",
        description=f"Scenic walking exploration of {session.constraints.origin}.",
        perk="+15 Exploration Wisdom",
    )
    session.candidate = candidate

    # Step 2: Query Transit Agent
    transit_query = TransitQuery(
        session_id=msg.session_id,
        candidate_id=candidate.id,
        origin=session.constraints.origin,
        destination_lat=candidate.lat,
        destination_lng=candidate.lng,
        departure_time="",
    )
    await ctx.send(transit_agent.address, transit_query)


@orchestrator_proto.on_message(TransitResult)
async def handle_transit_result(ctx: Context, sender: str, msg: TransitResult):
    session = active_sessions.get(msg.session_id)
    if not session:
        return

    ctx.logger.info(f"🚦 [Step 2 Received] TransitAgent returned {len(msg.options)} mobility options for session {msg.session_id}")
    session.transit_options = msg.options

    # Pick recommended mode
    chosen = next((opt for opt in msg.options if opt.mode == msg.recommended_mode), msg.options[0])
    session.chosen_transit = chosen

    # Compute resource slack:
    # Round-trip transit: 2 * duration
    roundtrip_transit = 2 * chosen.duration_minutes
    primary_dwell = session.candidate.estimated_dwell_minutes if session.candidate else 45
    transit_cost = chosen.estimated_cost
    roundtrip_transit_cost = 2 * transit_cost if chosen.mode != "driving" else transit_cost
    admission_cost = session.candidate.estimated_admission if session.candidate else 0.0

    time_used = roundtrip_transit + primary_dwell
    slack_time = max(0, session.constraints.duration_minutes - time_used)
    remaining_budget = max(0.0, session.constraints.budget_usd - (roundtrip_transit_cost + admission_cost))

    ctx.logger.info(
        f"📊 Feasibility Check: Total Time={session.constraints.duration_minutes}m, "
        f"Used={time_used}m -> Slack={slack_time}m | "
        f"Total Budget=${session.constraints.budget_usd:.2f} -> Remaining=${remaining_budget:.2f}"
    )

    # Step 3: Query Budget & Meal Agent
    meal_query = MealQuery(
        session_id=msg.session_id,
        available_budget=remaining_budget,
        available_slack_time=slack_time,
        cuisine_preference=session.constraints.vibe,
    )
    await ctx.send(budget_agent.address, meal_query)


@orchestrator_proto.on_message(MealResult)
async def handle_meal_result(ctx: Context, sender: str, msg: MealResult):
    session = active_sessions.get(msg.session_id)
    if not session:
        return

    ctx.logger.info(f"🍔 [Step 3 Received] BudgetAgent evaluated meal: recommended={msg.recommended} ({msg.spot_name})")
    session.meal_result = msg

    # Mark pipeline as complete to awaken the handle_chat_message coroutine
    session.pipeline_complete.set()


# Include Protocols
agent.include(orchestrator_proto)
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
