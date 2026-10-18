"""
simulate_asi1_chat.py: Simulates an ASI:One (asi1.ai) user sending a chat message
to the Quest Orchestrator agent using Fetch.ai's Agent Chat Protocol (ACP).

Simulates the ASI:One conversation flow:
1. Dispatches an ACP ChatMessage to Quest Orchestrator at http://localhost:8000/submit.
2. Receives immediate delivery confirmation (ChatAcknowledgement).
3. Receives and displays the asynchronous RPG Sidequest Log reply.
"""

import os
import sys
import json
import base64
import asyncio
from aiohttp import web
from dotenv import load_dotenv

# Ensure UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

from uagents import Agent
from uagents.communication import send_sync_message
from uagents.resolver import RulesBasedResolver
from uagents_core.identity import Identity
from uagents_core.contrib.protocols.chat import (
    ChatMessage,
    TextContent,
)

TARGET_SEED = os.getenv("AGENT_SEED_PHRASE", "fitlens").strip()
TARGET_AGENT_NAME = os.getenv("AGENT_NAME", "Quest Orchestrator").strip()

# Compute the target agent address deterministically from seed
target_temp = Agent(name="temp", seed=TARGET_SEED)
TARGET_ADDRESS = target_temp.address

# Simulated ASI:One user identity
CLIENT_SEED = "asi1-simulated-user-seed-la-hacks-2026"
client_identity = Identity.from_seed(CLIENT_SEED, 0)
CLIENT_ADDRESS = client_identity.address

# User prompt
DEFAULT_PROMPT = (
    "I have 2.5 hours and $35 starting from Westwood, looking for something chill and back by 6pm"
)
USER_PROMPT = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_PROMPT


async def handle_submit(request: web.Request) -> web.Response:
    """Handle incoming envelope posted by Quest Orchestrator back to the user."""
    try:
        data = await request.json()
        payload_raw = data.get("payload")
        if payload_raw:
            payload_str = base64.b64decode(payload_raw).decode("utf-8")
            payload_json = json.loads(payload_str)

            # Extract content from ChatMessage
            content_list = payload_json.get("content", [])
            reply_text = ""
            for item in content_list:
                if isinstance(item, dict) and "text" in item:
                    reply_text += item["text"] + " "

            future = request.app["reply_future"]
            if not future.done():
                future.set_result(reply_text.strip())

        return web.json_response({"status": "ok"})
    except Exception as e:
        print(f"Error parsing incoming envelope: {e}")
        return web.json_response({"error": str(e)}, status=400)


async def main():
    print("=" * 75)
    print(" 💬 [ASI:One Simulator] Simulating User Chat Session")
    print("=" * 75)
    print(f"Target Agent     : {TARGET_AGENT_NAME} ({TARGET_ADDRESS})")
    print(f"User Address     : {CLIENT_ADDRESS}")
    print(f"Message Prompt   : \"{USER_PROMPT}\"")
    print("-" * 75)

    # 1. Start aiohttp server on port 8001 to receive asynchronous ACP replies
    loop = asyncio.get_running_loop()
    reply_future = loop.create_future()

    app = web.Application()
    app["reply_future"] = reply_future
    app.router.add_post("/submit", handle_submit)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 8001)
    await site.start()

    # 2. Dispatch ChatMessage using Fetch.ai communication
    print(">>> [ASI:One] Sending ChatMessage to @quest-orchestrator...")
    chat_msg = ChatMessage(
        content=[TextContent(type="text", text=USER_PROMPT)]
    )

    resolver = RulesBasedResolver(rules={TARGET_ADDRESS: "http://127.0.0.1:8000/submit"})

    try:
        ack_res = await send_sync_message(
            destination=TARGET_ADDRESS,
            message=chat_msg,
            sender=client_identity,
            resolver=resolver,
            timeout=10,
        )
        print("⚡ [ACP Delivery Status] Delivery Confirmed by Quest Orchestrator!")
        if isinstance(ack_res, str):
            try:
                ack_obj = json.loads(ack_res)
                print(f"   ↳ Acknowledged Msg ID : {ack_obj.get('acknowledged_msg_id')}")
                print(f"   ↳ Timestamp           : {ack_obj.get('timestamp')}")
            except Exception:
                print(f"   ↳ Raw Ack: {ack_res}")
    except Exception as err:
        print(f"❌ Failed to send message: {err}")
        await runner.cleanup()
        return

    # 3. Wait for the asynchronous Sidequest Log reply
    print(">>> [ASI:One] Waiting for synthesized Sidequest Log...")
    try:
        reply_content = await asyncio.wait_for(reply_future, timeout=12.0)
        print("\n" + "=" * 25 + " ASI:ONE CONVERSATION UI " + "=" * 25)
        print(f"👤 User: \"{USER_PROMPT}\"\n")
        print(f"🤖 @quest-orchestrator:\n")
        print(reply_content)
        print("=" * 75)
        print("✨ [SUCCESS] Full ASI:One Agent Chat Protocol exchange completed!\n")
    except asyncio.TimeoutError:
        print("\n⚠️ [Timeout] Did not receive reply envelope within 12 seconds.")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
