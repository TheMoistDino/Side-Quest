"""
run.py: Top-Level Bureau Runner for Quest Orchestrator & Subagents.

Initializes a unified Fetch.ai Bureau managing all 4 agents in a single process:
- Quest Orchestrator (agent.py) -> Listens on port 8000 with public ngrok /submit endpoint
- Scout Agent (scout_agent.py) -> POI Discovery & Dwell Estimation
- Transit Agent (transit_agent.py) -> Multi-Modal Mobility & Routes
- Budget Agent (budget_agent.py) -> Opportunistic Culinary Integration
"""

import os
import sys

# Ensure UTF-8 output across Windows shells
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import warnings
import logging

# Suppress noisy ledger contract polling warnings and python deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
logging.getLogger("uagents.network").setLevel(logging.ERROR)

from dotenv import load_dotenv

load_dotenv()

import dns_resilience
dns_resilience.apply_dns_patches()

from uagents import Bureau

# Import all agents
from agent import agent as orchestrator_agent
from scout_agent import scout_agent
from dining_scout import dining_scout
from trails_scout import trails_scout
from culture_scout import culture_scout
from transit_agent import transit_agent
from budget_agent import budget_agent

PORT = int(os.getenv("PORT", "8000"))
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "https://liqueur-customize-nearby.ngrok-free.dev/submit").strip()


def main():
    print("=" * 70)
    print(" 🚀 Launching Quest Orchestrator Multi-Agent Bureau (Ensemble Active)")
    print("=" * 70)
    print(f"Server Port      : {PORT}")
    print(f"Public Webhook   : {AGENT_ENDPOINT}")
    print(f"REST Gateway     : http://127.0.0.1:{PORT}/api/quest (and /api/quest/plan)")
    print(f"ACP Webhook      : http://127.0.0.1:{PORT}/submit")
    print(f"Managed Agents   : ")
    print(f"  1. [Orchestrator]   {orchestrator_agent.name} ({orchestrator_agent.address})")
    print(f"  2. [Scout Ensemble] {scout_agent.name} ({scout_agent.address})")
    print(f"     ↳ [Dining]      {dining_scout.name} ({dining_scout.address})")
    print(f"     ↳ [Trails]      {trails_scout.name} ({trails_scout.address})")
    print(f"     ↳ [Culture]     {culture_scout.name} ({culture_scout.address})")
    print(f"  3. [Transit]        {transit_agent.name} ({transit_agent.address})")
    print(f"  4. [Budget]         {budget_agent.name} ({budget_agent.address})")
    print("-" * 70)

    # Initialize Bureau on port 8000
    bureau = Bureau(
        port=PORT,
        endpoint=[AGENT_ENDPOINT],
    )

    # Register all agents into the Bureau
    bureau.add(orchestrator_agent)
    bureau.add(scout_agent)
    bureau.add(dining_scout)
    bureau.add(trails_scout)
    bureau.add(culture_scout)
    bureau.add(transit_agent)
    bureau.add(budget_agent)

    print("All ensemble agents attached to Bureau. Starting event loops and listeners...")
    bureau.run()


if __name__ == "__main__":
    main()
