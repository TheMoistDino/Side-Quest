"""
test_client.py: Test and verification harness for Quest Orchestrator.

Provides two testing modes:
1. Local Simulator Mode: Tests NLP parameter extraction, feasibility math (ΔT, ΔC),
   opportunistic stop injection, and RPG-log formatting without network overhead.
2. ACP Network Mode: Launches a test uAgent communicating over Agent Chat Protocol (ACP)
   sending a live ChatMessage to the running Quest Orchestrator agent and receiving
   the ChatAcknowledgement and Sidequest itinerary.
"""

import os
import sys
import argparse

# Ensure UTF-8 output across Windows shells
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from planner import extract_constraints, synthesize_quest, render_rpg_log


SAMPLE_PROMPTS = [
    (
        "Westwood Chill & Boba",
        "I have 2.5 hours and $35 starting from Westwood, looking for something chill and back by 6pm",
    ),
    (
        "Downtown Art & Food Odyssey",
        "3 hours free, budget of $45 in Downtown LA for modern art and local eats",
    ),
    (
        "Santa Monica Coastal Sprint",
        "90 minutes free, $15 budget near Santa Monica, need an outdoor recharge",
    ),
    (
        "Zero-Dollar K-Town Walking Recon",
        "Free for 1 hour in Koreatown, $0 budget, just exploring",
    ),
]


def run_local_simulation(query_text: str = None):
    print("=" * 70)
    print(" 🎮 [SIMULATOR] Quest Orchestrator Core Planner Test")
    print("=" * 70)

    test_queries = [("Custom Query", query_text)] if query_text else SAMPLE_PROMPTS

    for label, prompt in test_queries:
        print(f"\n>>> TEST CASE: {label}")
        print(f"    Input Prompt: \"{prompt}\"")
        constraints = extract_constraints(prompt)
        print(f"    [Extracted Constraints]:")
        print(f"      - Temporal Window : {constraints.duration_minutes} mins")
        print(f"      - Fiscal Budget   : ${constraints.budget_usd:.2f}")
        print(f"      - Starting Origin : {constraints.origin}")
        print(f"      - Requested Vibe  : {constraints.vibe}")
        if constraints.return_cutoff:
            print(f"      - Return Cutoff   : {constraints.return_cutoff}")

        plan = synthesize_quest(constraints)
        print(f"    [Feasibility Breakdown]:")
        print(f"      - ΔT (Time Used)  : {plan.used_time_minutes}m / {plan.total_time_minutes}m (Slack: {plan.slack_time_minutes}m)")
        print(f"      - ΔC (Cost Used)  : ${plan.spent_budget_usd:.2f} / ${plan.total_budget_usd:.2f} (Reserve: ${plan.remaining_budget_usd:.2f})")
        print(f"      - Total Stops     : {len(plan.stops)} (Transit buffer: {plan.transit_buffer_minutes}m)")

        log_output = render_rpg_log(plan)
        print("\n" + "-" * 40 + " RPG LOG PREVIEW " + "-" * 40)
        # Handle UTF-8 output gracefully across different terminal environments
        try:
            print(log_output)
        except UnicodeEncodeError:
            print(log_output.encode("ascii", "replace").decode("ascii"))
        print("-" * 97)


def run_network_client(query_text: str, target_address: str = None):
    """Run an ACP-compliant uAgent to send a ChatMessage to Quest Orchestrator."""
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatMessage,
        ChatAcknowledgement,
        TextContent,
        chat_protocol_spec,
    )

    print("=" * 70)
    print(" 📡 [ACP NETWORK TEST] Launching Test Client Agent")
    print("=" * 70)

    # If target address not provided, calculate from seed phrase
    target_seed = os.getenv("AGENT_SEED_PHRASE", "quest orchestrator secret seed phrase for la hacks asi one challenge")
    from cosmpy.aerial.wallet import LocalWallet
    
    # Generate client on an ephemeral port
    client_agent = Agent(
        name="quest-test-client",
        port=8001,
        endpoint=["http://localhost:8001/submit"],
    )

    target_agent_addr = target_address
    if not target_agent_addr:
        # Determine orchestrator address using same seed
        temp_agent = Agent(name="temp", seed=target_seed)
        target_agent_addr = temp_agent.address

    print(f"Test Client Address : {client_agent.address}")
    print(f"Target Agent Address: {target_agent_addr}")
    print(f"Prompt Query        : \"{query_text}\"")
    print("-" * 70)

    client_proto = Protocol(spec=chat_protocol_spec)

    @client_agent.on_event("startup")
    async def send_initial_query(ctx: Context):
        ctx.logger.info(f"Connecting to Quest Orchestrator at {target_agent_addr}...")
        chat_msg = ChatMessage(
            content=[TextContent(type="text", text=query_text)]
        )
        await ctx.send(target_agent_addr, chat_msg)
        ctx.logger.info(f"Dispatched ChatMessage to {target_agent_addr}")

    @client_proto.on_message(ChatMessage)
    async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
        ctx.logger.info(f"Received reply ChatMessage from {sender}:")
        print("\n" + "=" * 30 + " RECEIVED AGENT RESPONSE " + "=" * 30)
        try:
            print(msg.text())
        except UnicodeEncodeError:
            print(msg.text().encode("ascii", "replace").decode("ascii"))
        print("=" * 85)
        # Send acknowledgement back
        await ctx.send(sender, ChatAcknowledgement(acknowledged_msg_id=msg.msg_id))
        ctx.logger.info("Test completed successfully! Stopping client...")
        sys.exit(0)

    @client_proto.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        ctx.logger.info(f"Target acknowledged message receipt (msg: {msg.acknowledged_msg_id})")

    client_agent.include(client_proto)
    client_agent.run()


def main():
    parser = argparse.ArgumentParser(description="Quest Orchestrator Test Harness")
    parser.add_argument("--network", action="store_true", help="Run live ACP network test against running agent")
    parser.add_argument("--query", type=str, default="", help="Custom query string to test")
    parser.add_argument("--target", type=str, default="", help="Cryptographic address of running Quest Orchestrator")

    args = parser.parse_args()

    if args.network:
        query = args.query or "I have 2.5 hours and $30 starting from Westwood, looking for something chill"
        run_network_client(query_text=query, target_address=args.target)
    else:
        run_local_simulation(query_text=args.query if args.query else None)


if __name__ == "__main__":
    main()
