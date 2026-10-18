"""
register.py: Programmatic registration script for Quest Orchestrator on Agentverse.

Utilizes Fetch.ai's uagents_core v2 registration utility to register the agent
with persistent Almanac synchronization and Agent Chat Protocol (ACP) support
for ASI:One (asi1.ai) integration.
"""

import os
import sys

# Ensure UTF-8 output across Windows shells
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from uagents_core.utils.registration import (
    AgentverseRequestError,
    RegistrationRequestCredentials,
    register_chat_agent,
)

AGENTVERSE_KEY = os.getenv("AGENTVERSE_KEY", "").strip()
AGENT_SEED_PHRASE = os.getenv("AGENT_SEED_PHRASE", "").strip()
AGENT_ENDPOINT = os.getenv("AGENT_ENDPOINT", "https://liqueur-customize-nearby.ngrok-free.dev/submit").strip()
AGENT_NAME = os.getenv("AGENT_NAME", "Quest Orchestrator").strip()

DESCRIPTION = (
    "Autonomous micro-itinerary planner turning spontaneous free time into "
    "RPG sidequests with transit, dwell time, and meal stops across Los Angeles."
)

README_TEXT = """# Quest Orchestrator (@quest-orchestrator)
**ASI:One & LA Hacks Track Submission**

Quest Orchestrator is an autonomous planning agent compliant with Fetch.ai's Agent Chat Protocol (ACP).
It transforms spontaneous free time windows into curated, RPG-styled micro-itineraries ('sidequests')
tailored to urban neighborhoods across Los Angeles.

### Core Capabilities
- **Temporal & Fiscal Balancing**: Accurately computes transit buffers, dwell intervals, and budget reserves.
- **Opportunistic Logistics**: Dynamically injects local snack and coffee waypoints when slack time permits.
- **ASI:One Ready**: Seamless multi-turn chat handling with direct response formatting.
"""

STARTER_PROMPTS = [
    "I have 2 hours and $25 starting from Westwood, looking for something chill.",
    "3 hours free, $40 budget in Downtown LA for art and food.",
    "90 minutes in Santa Monica with $15, need a quick adventure.",
]

METADATA = {
    "categories": ["lifestyle", "travel", "productivity", "gaming"],
    "is_public": "True",
    "version": "1.0.0",
}


def main():
    print("=" * 65)
    print(" [Fetch.ai / Agentverse] Registering Quest Orchestrator Agent")
    print("=" * 65)
    print(f"Agent Name     : {AGENT_NAME}")
    print(f"Endpoint       : {AGENT_ENDPOINT}")
    print(f"Seed Configured: {'[YES]' if AGENT_SEED_PHRASE else '[NO]'}")
    print(f"Key Configured : {'[YES]' if AGENTVERSE_KEY and AGENTVERSE_KEY != 'your_agentverse_api_key_here' else '[NO - PLACEHOLDER]'}")
    print("-" * 65)

    if not AGENTVERSE_KEY or AGENTVERSE_KEY == "your_agentverse_api_key_here":
        print("\n[!] WARNING: AGENTVERSE_KEY is missing or set to placeholder.")
        print("    1. Sign in to https://agentverse.ai")
        print("    2. Navigate to Profile / API Keys and create a key.")
        print("    3. Update AGENTVERSE_KEY in your .env file.")
        print("\nExiting registration script.")
        sys.exit(1)

    if not AGENT_SEED_PHRASE:
        print("\n[!] ERROR: AGENT_SEED_PHRASE is not set in .env.")
        sys.exit(1)

    print("Authenticating credentials with Agentverse...")
    credentials = RegistrationRequestCredentials(
        agent_seed_phrase=AGENT_SEED_PHRASE,
        agentverse_api_key=AGENTVERSE_KEY,
    )

    try:
        print(f"Sending registration request for '{AGENT_NAME}'...")
        register_chat_agent(
            name=AGENT_NAME,
            endpoint=AGENT_ENDPOINT,
            active=True,
            credentials=credentials,
            description=DESCRIPTION,
            readme=README_TEXT,
            starter_prompts=STARTER_PROMPTS,
            metadata=METADATA,
        )
        print("\n[SUCCESS] Agent successfully registered on Agentverse!")
        print("Agent is now live and discoverable via Agent Chat Protocol on ASI:One (asi1.ai)!")
    except AgentverseRequestError as err:
        print(f"\n[ERROR] Registration failed with AgentverseRequestError:\n{err}")
        if hasattr(err, "from_exc") and err.from_exc:
            print(f"Caused by underlying exception: {err.from_exc}")
        sys.exit(2)
    except Exception as ex:
        print(f"\n[ERROR] Unexpected error during registration: {ex}")
        sys.exit(3)


if __name__ == "__main__":
    main()
