"""
agent.py: Quest Orchestrator Agent (Primary Dispatcher & Dual Gateway).

Coordinates three specialized subagents running in a unified Bureau:
1. Scout Agent (scout_agent.py): POI discovery & dwell estimation
2. Transit & Mobility Agent (transit_agent.py): Multi-modal routing & fares
3. Budget & Meal Agent (budget_agent.py): Opportunistic culinary checkpoints

Supports two frontends simultaneously:
1. Custom Web/App Frontend: REST JSON endpoints (POST /api/quest and POST /api/quest/plan)
2. Fetch.ai ASI:One Interface: Agent Chat Protocol (ACP) over /submit webhook
"""

import os
import sys
import uuid
import time
import asyncio
import inspect
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from uagents import Agent, Context, Protocol
from uagents.asgi import ASGIServer
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
    QuestConstraints,
    extract_constraints,
    synthesize_quest,
    render_rpg_log,
    render_multiagent_rpg_log,
)

from scout_agent import scout_agent, query_poi_database, search_live_pois, verify_and_ground_candidates
from transit_agent import transit_agent, calculate_multi_modal_options
from budget_agent import budget_agent, SIT_DOWN_OPTIONS, SNACK_OPTIONS

from adapters import (
    FrontendQuestRequest,
    FrontendQuestResponse,
    adapt_frontend_request_to_constraints,
    adapt_acp_message_to_constraints,
    adapt_pipeline_to_frontend_response,
    adapt_pipeline_to_acp_response,
)

# Apply global CORS wrapper to ASGIServer so browser requests from Next.js (port 3000) succeed.
# Newer uagents (e.g. 0.26) already sends Access-Control-Allow-* on every response via uvicorn's
# default headers. Adding them again makes browsers reject the response ("multiple values '*, *'"),
# so only add the allow-headers when this uagents version doesn't.
_original_asgi_send = ASGIServer._asgi_send
_UAGENTS_SENDS_CORS = "Access-Control-Allow-Origin" in inspect.getsource(ASGIServer)

async def _cors_asgi_send(self, send, status_code=200, headers=None, body=None):
    if headers is None:
        headers = {}
    if "Content-Type" not in headers and "content-type" not in headers and body is not None:
        headers["Content-Type"] = "application/json"
    if not _UAGENTS_SENDS_CORS:
        headers["Access-Control-Allow-Origin"] = "*"
        headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, HEAD"
        headers["Access-Control-Allow-Headers"] = "*"
    headers["Access-Control-Max-Age"] = "86400"  # uagents doesn't set this; safe to add once
    return await _original_asgi_send(self, send, status_code=status_code, headers=headers, body=body)

ASGIServer._asgi_send = _cors_asgi_send


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
        self.all_candidates: List[QuestCandidate] = []
        self.transit_options: List[TransitOption] = []
        self.chosen_transit: Optional[TransitOption] = None
        self.meal_result: Optional[MealResult] = None
        self.pipeline_complete = asyncio.Event()


active_sessions: Dict[str, QuestSession] = {}


@agent.on_event("startup")
async def startup_handler(ctx: Context):
    ctx.logger.info("=" * 65)
    ctx.logger.info(f"🎮 {AGENT_NAME} ONLINE (Dual Gateway Multi-Agent Active)")
    ctx.logger.info(f"📌 Orchestrator Address : {agent.address}")
    ctx.logger.info(f"🔭 Scout Agent Address  : {scout_agent.address}")
    ctx.logger.info(f"🚦 Transit Agent Address: {transit_agent.address}")
    ctx.logger.info(f"🍔 Budget Agent Address : {budget_agent.address}")
    ctx.logger.info(f"🌐 Public Webhook (ACP) : {AGENT_ENDPOINT}")
    ctx.logger.info(f"🔌 Local Port           : {PORT}")
    ctx.logger.info(f"🚀 REST Routes          : POST /api/quest, POST /api/quest/plan")
    ctx.logger.info(f"💬 Protocol             : Fetch.ai Agent Chat Protocol (ACP)")
    ctx.logger.info("Ready for dual-frontend sidequest orchestration!")
    ctx.logger.info("=" * 65)


# ==============================================================================
# Shared Multi-Agent Pipeline Runner
# ==============================================================================

async def run_multiagent_pipeline(
    constraints: QuestConstraints,
    ctx: Optional[Context] = None,
) -> Tuple[QuestCandidate, TransitOption, List[TransitOption], Optional[MealResult], List[QuestCandidate]]:
    """
    Core orchestration pipeline shared by both the Custom Frontend (REST)
    and the ASI:One (ACP) entry points.
    
    1. Executes inter-agent RPC via ctx.send if available inside the Bureau.
    2. Employs resilient fallback to deterministic subagent worker calls upon timeout.
    """
    session_id = str(uuid.uuid4())[:8]
    session = QuestSession(session_id=session_id, user_sender="orchestrator", constraints=constraints)
    active_sessions[session_id] = session

    pipeline_succeeded = False

    if ctx is not None:
        try:
            # Query Scout Agent with grounded constraints
            scout_query = ScoutQuery(
                session_id=session_id,
                query_area=constraints.origin,
                category=constraints.vibe,
                max_admission=constraints.budget_usd,
                departure_time=getattr(constraints, "departure_time", None),
                return_cutoff=getattr(constraints, "return_cutoff", None),
            )
            await ctx.send(scout_agent.address, scout_query)

            # Await full inter-agent pipeline resolution with extended async buffer (35s)
            await asyncio.wait_for(session.pipeline_complete.wait(), timeout=35.0)
            if session.candidate and session.chosen_transit:
                pipeline_succeeded = True
        except Exception as err:
            if ctx and hasattr(ctx, "logger"):
                ctx.logger.info(f"Notice: inter-agent dispatch fallback: {err}. Executing subagent workers directly.")

    # Resilient subagent worker execution if network wait timed out or direct execution
    if not pipeline_succeeded or session.candidate is None:
        # Step 1: Scout Subagent Worker with live HTTP validation & dwell bounding
        candidates = search_live_pois(constraints.origin, constraints.vibe, constraints.budget_usd)
        if not candidates:
            candidates = query_poi_database(
                area=constraints.origin,
                category=constraints.vibe,
                max_admission=constraints.budget_usd,
                departure_time=getattr(constraints, "departure_time", None),
                return_cutoff=getattr(constraints, "return_cutoff", None),
            )

        candidates = await verify_and_ground_candidates(
            candidates,
            departure_time=getattr(constraints, "departure_time", None),
            return_cutoff=getattr(constraints, "return_cutoff", None),
        )

        session.all_candidates = candidates
        candidate = candidates[0] if candidates else QuestCandidate(
            id="default-poi",
            name=f"Historic Walk around {constraints.origin}",
            lat=34.0689,
            lng=-118.4452,
            estimated_admission=0.0,
            estimated_dwell_minutes=45,
            opening_hours="Open 24/7",
            description=f"Scenic walking exploration of {constraints.origin}.",
            perk="+15 Exploration Wisdom",
            address=f"Central Plaza, {constraints.origin}, CA",
            category="Walking Tour",
            rating=4.7,
            review_count=350,
            review_summary=f"Scenic walking route charting architectural gems in {constraints.origin}.",
        )
        session.candidate = candidate

        # Step 2: Transit Subagent Worker
        transit_options, recommended_mode = calculate_multi_modal_options(
            origin_str=constraints.origin,
            dest_lat=candidate.lat,
            dest_lng=candidate.lng,
        )
        session.transit_options = transit_options
        session.chosen_transit = next((opt for opt in transit_options if opt.mode == recommended_mode), transit_options[0])

        # Step 3: Budget Subagent Worker (Feasibility & Slack)
        roundtrip_transit = 2 * session.chosen_transit.duration_minutes
        primary_dwell = candidate.estimated_dwell_minutes
        transit_cost = session.chosen_transit.estimated_cost
        roundtrip_transit_cost = 2 * transit_cost if session.chosen_transit.mode != "driving" else transit_cost
        admission_cost = candidate.estimated_admission

        time_used = roundtrip_transit + primary_dwell
        slack_time = max(0, constraints.duration_minutes - time_used)
        remaining_budget = max(0.0, constraints.budget_usd - (roundtrip_transit_cost + admission_cost))

        if slack_time >= 45 and remaining_budget >= 15.0:
            dining_candidates = [s for s in SIT_DOWN_OPTIONS if s["cost"] <= remaining_budget and s["dwell"] <= (slack_time - 10)]
            chosen_meal = dining_candidates[0] if dining_candidates else SIT_DOWN_OPTIONS[0]
            session.meal_result = MealResult(
                session_id=session_id,
                recommended=True,
                spot_name=chosen_meal["name"],
                estimated_cost=chosen_meal["cost"],
                dwell_mins=chosen_meal["dwell"],
                reasoning=f"Optimal slack ({slack_time}m) allows sit-down culinary checkpoint: {chosen_meal['reasoning']}",
                perk=chosen_meal["perk"],
            )
        elif slack_time >= 20 and remaining_budget >= 4.50:
            snack_candidates = [s for s in SNACK_OPTIONS if s["cost"] <= remaining_budget and s["dwell"] <= (slack_time - 5)]
            chosen_snack = snack_candidates[0] if snack_candidates else SNACK_OPTIONS[0]
            session.meal_result = MealResult(
                session_id=session_id,
                recommended=True,
                spot_name=chosen_snack["name"],
                estimated_cost=chosen_snack["cost"],
                dwell_mins=chosen_snack["dwell"],
                reasoning=f"Tactical slack ({slack_time}m) allows quick supply drop: {chosen_snack['reasoning']}",
                perk=chosen_snack["perk"],
            )
        else:
            session.meal_result = MealResult(
                session_id=session_id,
                recommended=False,
                spot_name=None,
                estimated_cost=0.0,
                dwell_mins=0,
                reasoning="Schedule or funds are tightly allocated; preserving return deadline.",
                perk=None,
            )

    active_sessions.pop(session_id, None)
    return (
        session.candidate,
        session.chosen_transit,
        session.transit_options,
        session.meal_result,
        session.all_candidates,
    )


# ==============================================================================
# REST HTTP Endpoints for Custom Web/App Frontend
# ==============================================================================

@agent.on_rest_post("/api/quest", FrontendQuestRequest, FrontendQuestResponse)
async def handle_rest_quest(ctx: Context, req: FrontendQuestRequest) -> FrontendQuestResponse:
    """
    Primary REST endpoint matching the Next.js frontend's target in lib/api.ts.
    Receives QuestRequest JSON, runs through multi-agent orchestration,
    and returns exact QuestResponse JSON.
    """
    b_val = req.budgetPerPerson if isinstance(req.budgetPerPerson, (int, float)) else 35.0
    p_val = req.groupSize if isinstance(req.groupSize, int) else 1
    loc_val = f"({req.location.lat:.4f}, {req.location.lng:.4f})" if (req.location and isinstance(req.location.lat, (int, float))) else "default"
    ctx.logger.info(
        f"🌐 [REST /api/quest] Ingestion: Category='{req.category}', "
        f"Budget=${b_val:.2f}, Party={p_val}, Location={loc_val}"
    )

    # 1. Path A: Ingest and normalize frontend payload
    constraints = adapt_frontend_request_to_constraints(req)

    # 2. Execute multi-agent orchestration
    cand, chosen_transit, all_transits, meal_res, all_cands = await run_multiagent_pipeline(constraints, ctx)

    # 3. Format into exact FrontendQuestResponse model
    response = adapt_pipeline_to_frontend_response(
        constraints=constraints,
        candidate=cand,
        chosen_transit=chosen_transit,
        all_transit_options=all_transits,
        meal_res=meal_res,
        req=req,
        all_candidates=all_cands,
    )

    ctx.logger.info(f"✨ [REST /api/quest] Successfully generated {len(response.quests)} curated quests for frontend.")
    return response


@agent.on_rest_post("/api/quest/plan", FrontendQuestRequest, FrontendQuestResponse)
async def handle_rest_quest_plan(ctx: Context, req: FrontendQuestRequest) -> FrontendQuestResponse:
    """Convenience alias route for POST /api/quest/plan."""
    ctx.logger.info("🌐 [REST /api/quest/plan] Alias route invoked.")
    return await handle_rest_quest(ctx, req)


# ==============================================================================
# ASI:One Chat Message Handling (Agent Chat Protocol via /submit)
# ==============================================================================

@chat_proto.on_message(ChatMessage)
async def handle_chat_message(ctx: Context, sender: str, msg: ChatMessage):
    """
    Handles incoming conversational messages from Fetch.ai ASI:One via ACP.
    """
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

    ctx.logger.info(f"🔍 Analyzing ASI:One query: '{incoming_query}'")

    # 3. Path B: Ingest via adapter
    constraints = adapt_acp_message_to_constraints(incoming_query)

    # 4. Execute shared multi-agent orchestration
    cand, chosen_transit, all_transits, meal_res, _ = await run_multiagent_pipeline(constraints, ctx)

    # 5. Format ACP response (Markdown Log & Interactive Card)
    response_text, _ = adapt_pipeline_to_acp_response(
        constraints=constraints,
        candidate=cand,
        chosen_transit=chosen_transit,
        all_transit_options=all_transits,
        meal_res=meal_res,
    )

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
# Inter-Agent RPC Handlers (Orchestrator Pipeline inside Bureau)
# ==============================================================================

orchestrator_proto = Protocol(name="OrchestratorPipelineProtocol", version="1.0.0")


@orchestrator_proto.on_message(ScoutResult)
async def handle_scout_result(ctx: Context, sender: str, msg: ScoutResult):
    session = active_sessions.get(msg.session_id)
    if not session:
        return

    ctx.logger.info(f"🔭 [Step 1 Received] ScoutAgent returned {len(msg.candidates)} candidates for session {msg.session_id}")
    session.all_candidates = msg.candidates

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
        address=f"Central Plaza, {session.constraints.origin}, CA",
        category="Walking Tour",
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

    # Mark pipeline as complete to awaken the waiting coroutine
    session.pipeline_complete.set()


# Include Protocols
agent.include(orchestrator_proto)
agent.include(chat_proto, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
