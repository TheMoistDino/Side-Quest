# Quest Orchestrator 🎮
**LA Hacks Project | Fetch.ai & ASI:One Track**

> **Agent Handle**: `@quest-orchestrator`  
> **Protocol**: Fetch.ai Agent Chat Protocol (ACP) `0.3.0`  
> **Network**: Agentverse Almanac & ASI:One (`asi1.ai`)  

Quest Orchestrator is an autonomous planning agent built for the Fetch.ai / ASI:One challenge. It converts spontaneous free-time windows into actionable, mathematically balanced "sidequest" micro-itineraries across Los Angeles neighborhoods.

---

## ⚡ Key Features

1. **Agent Chat Protocol (ACP) Compliant**:
   - Native integration with `uagents_core.contrib.protocols.chat` (`ChatMessage`, `ChatAcknowledgement`, `TextContent`).
   - Responds directly to judges inside the **ASI:One chat interface** (`https://asi1.ai`).

2. **Temporal & Fiscal Balancing Engine**:
   - **Temporal Budget ($\Delta T$)**: Dynamically budgets transit buffers (15–30 mins), primary objective dwell time (30–90 mins), and slack time.
   - **Fiscal Budget ($\Delta C$)**: Strictly respects budget limits (including \$0 / free adventures), tracking spent vs. reserve funds.
   - **Opportunistic Logistics**: Automatically injects a local snack or coffee stop (e.g. boba, al pastor street tacos, artisanal matcha) whenever remaining slack time is $\ge 30$ mins and funds permit.

3. **Immersive RPG "Sidequest Log" Formatting**:
   - Quest rank classification (Rank C Micro-Patrol up to Rank S Epic Campaign).
   - Timestamped itinerary with fast-travel buffers and waypoint intel.
   - RPG rewards, character perks (e.g. `+25 Mental Resilience`, `+10 Agility`), and tactical recon tips.

---

## 📁 Multi-Agent Bureau Architecture

```
Side-Quest/
├── .env.example          # Environment variables template
├── .env                  # Your local environment configuration
├── requirements.txt      # uAgents, uagents-core, pydantic, and dependencies
├── schemas.py            # Typed Pydantic/uAgents Model schemas for inter-agent RPC
├── scout_agent.py        # Scout Agent (POI Discovery & Dwell Estimation)
├── transit_agent.py      # Transit & Mobility Agent (Multi-modal Routing & Fares)
├── budget_agent.py       # Budget & Meal Agent (Opportunistic Culinary Checkpoints)
├── agent.py              # Quest Orchestrator (Primary Dispatcher & ACP Handler)
├── run.py                # Top-level Bureau runner managing all 4 agents
├── planner.py            # Core NLP extraction & Multi-Agent RPG Log generator
├── register.py           # Programmatic Agentverse v2 registration script
├── test_flow.py          # Multi-agent pipeline verification test harness
├── simulate_asi1_chat.py # Live ASI:One ACP chat simulation client
└── README.md             # Setup and deployment documentation
```

---

## 🚀 Quickstart & Setup

### 1. Clone & Set Up Virtual Environment

```bash
# Navigate to the project directory
cd Side-Quest

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)

Copy the template:
```bash
cp .env.example .env
```

Ensure `.env` contains your Agentverse credentials and ngrok tunnel endpoint:
```ini
# Agentverse & Fetch.ai Credentials
AGENTVERSE_KEY=your_actual_agentverse_api_key_here
AGENT_SEED_PHRASE=quest orchestrator secret seed phrase for la hacks asi one challenge

# Agent Server Configuration
PORT=8000
AGENT_ENDPOINT=https://liqueur-customize-nearby.ngrok-free.dev/submit
AGENT_NAME=Quest Orchestrator
```

> [!NOTE]
> - Obtain your `AGENTVERSE_KEY` from [Agentverse.ai](https://agentverse.ai) -> **Profile** -> **API Keys**.
> - The `AGENT_SEED_PHRASE` is the cryptographic root for the agent's bech32 address on Fetch.ai's network.

---

## 🛰️ Tunneling & Registration

### Step 1: Start your ngrok Tunnel
In a separate terminal, forward local port 8000 to your public endpoint:
```bash
ngrok http 8000 --url=liqueur-customize-nearby.ngrok-free.dev
```

### Step 2: Register on Agentverse
Run the programmatic registration script to register the agent with the Agentverse Almanac and configure chat starter prompts:
```bash
python register.py
```
*When successful, this establishes permanent Almanac routing for `@quest-orchestrator`.*

---

## 🏃 Running the Multi-Agent Bureau

Launch the top-level runner to start the Orchestrator and all three subagents (`ScoutAgent`, `TransitAgent`, `BudgetAgent`) together in a single `uagents.Bureau` process:
```bash
python run.py
```

You will see output confirming all four agents initialized:
```
======================================================================
 🚀 Launching Quest Orchestrator Multi-Agent Bureau
======================================================================
Server Port      : 8000
Public Webhook   : https://liqueur-customize-nearby.ngrok-free.dev/submit
Managed Agents   : 
  1. [Orchestrator] Quest Orchestrator (agent1qtxgg4nhuumtnmt5gr2cug3e3hejvs47c5u9lfvtnnduj8tec073qer70z3)
  2. [Scout]        Scout Agent (agent1qvc7gj9lucaamk9z9cnsxj3vgqncpctfe6h5k0kcwweha2pk20p45xznj74)
  3. [Transit]      Transit Agent (agent1qg4hzfxgqamfxz7av5prx7syah5qzf5h4nzjs9dtnpnytyzw7u74qaeesgn)
  4. [Budget]       Budget Agent (agent1qdul4v9set79fkt9jlssd5zjxwtv6702897j3xjmuu33y6szny6akdqm8xt)
----------------------------------------------------------------------
Starting server on http://0.0.0.0:8000 (Press CTRL+C to quit)
Ready for ASI:One multi-agent sidequest delegation!
```

---

## 🧪 Verification & Testing

### 1. Multi-Agent Pipeline Verification (`test_flow.py`)
Run the comprehensive multi-agent pipeline verification test to trace each hop (Scout POI discovery, Transit multi-modal calculation, Budget dining evaluation, and RPG synthesis):
```bash
python test_flow.py
```

### 2. Simulated ASI:One User Chat (`simulate_asi1_chat.py`)
With `run.py` running, run the ASI:One simulator to simulate a live user sending an Agent Chat Protocol message:
```bash
python simulate_asi1_chat.py
```
You can pass any custom prompt:
```bash
python simulate_asi1_chat.py '3 hours free, $45 budget in Downtown LA for modern art and food'
```
*This verifies the full Fetch.ai ACP cycle: delivery confirmation followed by the multi-agent synthesized Sidequest Log.*

### 3. ASI:One Judge Interaction (`asi1.ai`)
1. Go to [ASI:One](https://asi1.ai).
2. Start a conversation with `@quest-orchestrator` or search for **Quest Orchestrator**.
3. Send sample prompts such as:
   - *"I have 2 hours and $25 starting from Westwood, looking for something chill."*
   - *"3 hours free, $45 budget in Downtown LA for modern art and food."*
   - *"Free for 1 hour in Koreatown, $0 budget, just exploring."*
4. The agent coordinates its three subagents and returns the formatted RPG Sidequest Log with multi-modal routes and food perks!
