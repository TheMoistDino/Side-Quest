"""
budget_agent.py: Budget & Meal Agent for opportunistic dining integration.

Subagent in Quest Orchestrator Bureau:
- Receives: MealQuery
- Replies: MealResult
- Logic:
  * Slack >= 45 min & Budget >= $15: Sit-down / fast-casual dining recommendation.
  * Slack 20-44 min & Budget >= $5: Grab-and-go snack or specialty coffee.
  * Otherwise: recommended=False (schedule/funds strictly conserved).
"""

import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv()

from uagents import Agent, Context, Protocol
from schemas import MealQuery, MealResult

BUDGET_SEED = os.getenv("BUDGET_SEED_PHRASE", "budget-subagent-seed-phrase-la-hacks-quest").strip()

budget_agent = Agent(
    name="Budget Agent",
    seed=BUDGET_SEED,
)

SIT_DOWN_OPTIONS: List[Dict[str, Any]] = [
    {
        "name": "Tsujita LA Artisan Noodle (Tonkotsu Tsukemen)",
        "cost": 18.0,
        "dwell": 45,
        "reasoning": "Rich 60-hour broth with slow-cooked pork belly and thick dip noodles.",
        "perk": "+30 Umami Surge, Satiety Maxima",
    },
    {
        "name": "Grand Central Market Tacos & Provisions",
        "cost": 16.0,
        "dwell": 40,
        "reasoning": "Handmade carnitas tacos and artisan iced horchata.",
        "perk": "+25 Gastronomy Insight, +10 Morale",
    },
    {
        "name": "Sun Nong Dan Galbi Jjim Rice Bowl",
        "cost": 22.0,
        "dwell": 45,
        "reasoning": "Tender braised short ribs served with steaming rice and kimchi.",
        "perk": "+40 Strength, Legendary Feast",
    },
    {
        "name": "Bay Cities Deli Sandwich & San Pellegrino",
        "cost": 15.0,
        "dwell": 35,
        "reasoning": "Crisp Italian bread with cold-cut meats and spicy pepper relish.",
        "perk": "+35 Stamina Reserve",
    },
]

SNACK_OPTIONS: List[Dict[str, Any]] = [
    {
        "name": "Boba Time Roasted Milk Tea with Herbal Jelly",
        "cost": 6.50,
        "dwell": 20,
        "reasoning": "Chilled caffeinated elixir with brown sugar sweetness for stamina recharge.",
        "perk": "+10 Hydration, Sugar Rush",
    },
    {
        "name": "Al Pastor Street Taco Stand (2x Double Tortilla)",
        "cost": 7.00,
        "dwell": 20,
        "reasoning": "Freshly sliced pork from the spinning trompo with pineapple and salsa verde.",
        "perk": "+15 Energy Replenishment",
    },
    {
        "name": "Diddy Riese Warm Cookie Sandwich",
        "cost": 4.50,
        "dwell": 15,
        "reasoning": "Two fresh oven-baked chocolate chip cookies with premium vanilla ice cream.",
        "perk": "+15 Morale, Sweet Tooth Buff",
    },
    {
        "name": "Sidecar Doughnuts Huckleberry Sourdough Donut",
        "cost": 6.00,
        "dwell": 15,
        "reasoning": "Warm sourdough donut fried fresh every hour with tangy huckleberry glaze.",
        "perk": "+10 Swiftness",
    },
]


budget_proto = Protocol(name="BudgetProtocol", version="1.0.0")


@budget_proto.on_message(MealQuery)
async def handle_meal_query(ctx: Context, sender: str, msg: MealQuery):
    ctx.logger.info(
        f"🍔 MealQuery from {sender} [Session: {msg.session_id}] | "
        f"Available Budget: ${msg.available_budget:.2f}, Slack Time: {msg.available_slack_time}m"
    )

    slack = msg.available_slack_time
    budget = msg.available_budget

    # Condition 1: Slack >= 45m and Budget >= $15 -> Sit-down / fast-casual dining
    if slack >= 45 and budget >= 15.0:
        candidates = [s for s in SIT_DOWN_OPTIONS if s["cost"] <= budget and s["dwell"] <= (slack - 10)]
        if not candidates:
            candidates = SIT_DOWN_OPTIONS[:1]

        chosen = candidates[0]
        reply = MealResult(
            session_id=msg.session_id,
            recommended=True,
            spot_name=chosen["name"],
            estimated_cost=chosen["cost"],
            dwell_mins=chosen["dwell"],
            reasoning=f"Optimal slack ({slack}m) and reserve funds (${budget:.2f}) allow a complete sit-down culinary checkpoint: {chosen['reasoning']}",
            perk=chosen["perk"],
        )
        ctx.logger.info(f"✅ Recommended sit-down meal: {chosen['name']} (${chosen['cost']})")

    # Condition 2: Slack between 20-44m and Budget >= $4.50 -> Grab-and-go / coffee / snack
    elif slack >= 20 and budget >= 4.50:
        candidates = [s for s in SNACK_OPTIONS if s["cost"] <= budget and s["dwell"] <= (slack - 5)]
        if not candidates:
            candidates = SNACK_OPTIONS[:1]

        chosen = candidates[0]
        reply = MealResult(
            session_id=msg.session_id,
            recommended=True,
            spot_name=chosen["name"],
            estimated_cost=chosen["cost"],
            dwell_mins=chosen["dwell"],
            reasoning=f"Tactical slack ({slack}m) permits a rapid supply drop: {chosen['reasoning']}",
            perk=chosen["perk"],
        )
        ctx.logger.info(f"✅ Recommended opportunistic snack: {chosen['name']} (${chosen['cost']})")

    # Condition 3: Otherwise -> Tight budget or schedule
    else:
        reasoning = (
            f"Schedule or funds are tightly allocated: {slack}m slack time and ${budget:.2f} funds remaining. "
            "Prioritizing primary quest waypoint and guaranteeing zero-risk return deadline."
        )
        reply = MealResult(
            session_id=msg.session_id,
            recommended=False,
            spot_name=None,
            estimated_cost=0.0,
            dwell_mins=0,
            reasoning=reasoning,
            perk=None,
        )
        ctx.logger.info(f"🛑 No dining stop recommended (slack: {slack}m, budget: ${budget:.2f})")

    await ctx.send(sender, reply)


budget_agent.include(budget_proto)


if __name__ == "__main__":
    budget_agent.run()
