# Side Quest 🎮

**LA Hacks Project | Fetch.ai & ASI:One Track**

> **Live ASI:One Handle**: `@quest-orchestrator`  
> **Protocol**: Fetch.ai Agent Chat Protocol (ACP) `0.3.0`  
> **Network**: Agentverse Almanac & ASI:One (`asi1.ai`)  
> **Frontend**: Next.js App Router · TypeScript · Tailwind CSS v4 · react-leaflet + OpenStreetMap  

---

## 🧭 Overview

People want to hang out but don't know what to do. **Side Quest** turns spontaneous free-time windows into actionable, mathematically balanced "sidequest" micro-itineraries across Los Angeles neighborhoods.

The project consists of:
1. **Interactive Frontend ("Side Quest Board")**: A minimal, dark-mode one-question-per-screen wizard asking six quick questions (vibe, time window, budget, location, distance, party size), visualizing multi-stop route timelines, budgets, reviews, and interactive maps.
2. **Autonomous Multi-Agent Backend ("Quest Orchestrator")**: A Fetch.ai `uagents.Bureau` coordinating specialized agents (Scout, Transit, Budget) using the Agent Chat Protocol (ACP) to balance temporal dwell times, transit buffers, and dining perks.

---

## ⚡ Key Features

1. **Autonomous Multi-Agent Bureau**:
   - **Scout Agent**: POI discovery, vibe matching, dwell-time estimation, and review intelligence.
   - **Transit Agent**: Multi-modal travel calculations (driving, walking, rideshare, public transit) and route timings.
   - **Budget & Meal Agent**: Opportunistic culinary stops (boba, matcha, tacos) when slack time $\ge 30$ mins and funds permit.
   - **Quest Orchestrator**: Central dispatcher managing inter-agent communications and synthesis.

2. **Agent Chat Protocol (ACP) Compliant**:
   - Responds natively within the **ASI:One chat interface** (`https://asi1.ai`).
   - Handles `ChatMessage`, `ChatAcknowledgement`, and formatted text responses.

3. **Temporal & Fiscal Balancing Engine**:
   - **Temporal Budget ($\Delta T$)**: Dynamically buffers transit, dwell times, and slack intervals.
   - **Fiscal Budget ($\Delta C$)**: Strictly caps spending per person (supporting \$0 / free adventures).

4. **Immersive RPG "Sidequest Log" & Web UI**:
   - Quest rank classification (Rank C Micro-Patrol up to Rank S Epic Campaign).
   - Stop timeline with travel connectors, fast-travel buffers, waypoint intel, reviews, and interactive Leaflet map routes.

---

## 📁 Repository Structure

```
Side-Quest/
├── app/                      # Next.js App Router (layout, page, globals.css, icon)
├── components/               # React UI components
│   ├── board/                # QuestBoard, QuestCard, Results, StatBlock, AnswerSummary
│   ├── detail/               # QuestDetail, StopTimeline, StopCard, RouteMap, Reviews
│   ├── states/               # LoadingState, ErrorState, EmptyState
│   └── wizard/               # 6-step form wizard (Vibe, ClockWindow, BigRange, etc.)
├── lib/
│   ├── api.ts                # Frontend API client (mock vs live backend switcher)
│   ├── format.ts             # Display formatters (money, duration, distance, time)
│   └── mock.ts               # Sample LA micro-itineraries for mock mode
├── types/
│   └── quest.ts              # Canonical shared TypeScript data contracts
├── agent.py                  # Primary Quest Orchestrator (ACP handler & dispatcher)
├── scout_agent.py            # Scout Agent (POI Discovery & Dwell Estimation)
├── transit_agent.py          # Transit & Mobility Agent (Multi-modal routing & fares)
├── budget_agent.py           # Budget & Meal Agent (Opportunistic Culinary stops)
├── planner.py                # Core NLP extraction & Multi-Agent RPG Log generator
├── schemas.py                # Typed Pydantic/uAgents Model schemas for inter-agent RPC
├── run.py                    # Top-level runner managing all 4 agents in a Bureau
├── register.py               # Programmatic Agentverse v2 registration script
├── test_flow.py              # End-to-end multi-agent pipeline verification test harness
├── simulate_asi1_chat.py     # Live ASI:One ACP chat simulation client
├── package.json              # Next.js & Node dependencies
├── requirements.txt          # Python dependencies (uagents, uagents-core, pydantic)
├── .env.example              # Template configuration for frontend & agents
└── README.md
```

---

## 🚀 Quickstart

### 1. Frontend Setup (Next.js)

```bash
# Install dependencies
npm install

# Copy environment variables template
cp .env.example .env.local

# Start development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

Additional commands:
- `npm run lint` — Lint code
- `npm run build` — Production build

---

### 2. Multi-Agent Bureau Setup (Python)

```bash
# Create and activate Python virtual environment
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install Python requirements
pip install -r requirements.txt
```

#### Configure `.env`

Copy `.env.example` to `.env` and configure your keys:
```ini
# Agentverse & Fetch.ai Credentials
AGENTVERSE_KEY=your_actual_agentverse_api_key_here
AGENT_SEED_PHRASE=fitlens

# Agent Server Configuration
PORT=8000
AGENT_ENDPOINT=https://liqueur-customize-nearby.ngrok-free.dev/submit
AGENT_NAME=Quest Orchestrator
```

> [!NOTE]
> - Obtain your `AGENTVERSE_KEY` from [Agentverse.ai](https://agentverse.ai) -> **Profile** -> **API Keys**.
> - The `AGENT_SEED_PHRASE` serves as the cryptographic root for the agent's bech32 address.

#### Start Tunnel & Run Agents

1. **ngrok Tunnel**:
   ```bash
   ngrok http 8000 --url=liqueur-customize-nearby.ngrok-free.dev
   ```

2. **Register on Agentverse** (one-time or when updating endpoints):
   ```bash
   python register.py
   ```

3. **Start the Multi-Agent Bureau**:
   ```bash
   python run.py
   ```

---

## 🔌 Frontend & Backend Integration

### Mock vs. Real Backend

All frontend fetching runs through `generateQuests(req)` in [`lib/api.ts`](lib/api.ts):

| `NEXT_PUBLIC_USE_MOCK` | Behavior |
| --- | --- |
| `true` *(default)* | Returns sample LA sidequests from [`lib/mock.ts`](lib/mock.ts) after a 1.5s delay. |
| `false` | Sends `POST {NEXT_PUBLIC_API_BASE_URL}/api/quest` with a `QuestRequest` payload. |

`NEXT_PUBLIC_API_BASE_URL` says where the backend lives. Leave it empty to call the same origin as the Next.js app; to use the Python agent server, point it at that server:

```bash
NEXT_PUBLIC_USE_MOCK=false
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000   # agent server's PORT
```

Restart `npm run dev` after changing either value (`NEXT_PUBLIC_*` variables are inlined at startup).

To test specific UI states in mock mode:
- `NEXT_PUBLIC_MOCK_SCENARIO=error` — Preview error screen with retry
- `NEXT_PUBLIC_MOCK_SCENARIO=empty` — Preview "no quests found" screen

### Data Contract (`types/quest.ts`)

The frontend wizard sends a `QuestRequest`:
- `category`: `food` | `outdoors` | `arts` | `nightlife` | `games` | `surprise me`
- `startTime` / `endTime`: ISO 8601 in UTC (`Date#toISOString()`)
- `budgetPerPerson`: Number (0–100 in steps of 5, or custom number up to 1000)
- `maxDistanceMiles`: Number (1–30, or custom up to 100)
- `location`: `{ lat, lng, label }`
- `groupSize`: Number (1–20)

---

## 🧪 Verification & Testing

### 1. Multi-Agent Pipeline Verification (`test_flow.py`)
Traces each agent hop (Scout POI discovery, Transit multi-modal routing, Budget dining evaluation, and synthesis):
```bash
python test_flow.py
```

### 2. Simulated ASI:One ACP Chat (`simulate_asi1_chat.py`)
Sends simulated ACP messages to the running Bureau:
```bash
python simulate_asi1_chat.py '3 hours free, $45 budget in Downtown LA for modern art and food'
```

### 3. Live ASI:One Chat Interface (`asi1.ai`)
1. Visit [ASI:One](https://asi1.ai).
2. Chat with `@quest-orchestrator`.
3. Example query: *"I have 2 hours and $25 starting from Westwood, looking for something chill."*
