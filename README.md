# Side Quest Board

People want to hang out but don't know what to do. Side Quest asks six quick questions (vibe, time window, budget, starting point, distance, party size) and an AI backend returns a few **side quests**: short multi-stop plans with costs, travel, and summaries of real reviews.

Stack: Next.js (App Router) · TypeScript · Tailwind CSS v4 · react-leaflet + OpenStreetMap tiles. No auth, no database, no state library.

---

## Frontend notes

### Run it

```bash
npm install
cp .env.example .env.local   # first time only
npm run dev                  # http://localhost:3000
```

Other scripts: `npm run lint`, `npm run build`.

### Mock vs. real backend

All fetching goes through one function, `generateQuests(req)` in [`lib/api.ts`](lib/api.ts).

| `NEXT_PUBLIC_USE_MOCK` | Behavior |
| --- | --- |
| `true` *(default, also used when unset)* | Returns the 3 LA quests from [`lib/mock.ts`](lib/mock.ts) after a 1.5s delay. |
| `false` | `POST /api/quest` with a `QuestRequest` body. A non-2xx `ApiError` body is shown as-is, with a retry button. |

**To switch to the real backend**, set this in `.env.local` and restart `npm run dev` (`NEXT_PUBLIC_*` values are baked in at startup):

```bash
NEXT_PUBLIC_USE_MOCK=false
```

Nothing else changes.

Previewing UI states in mock mode only: `NEXT_PUBLIC_MOCK_SCENARIO=error` shows the error screen, and `NEXT_PUBLIC_MOCK_SCENARIO=empty` shows the "no quests" screen.

### Folder ownership (avoids merge conflicts)

| Owner | Paths |
| --- | --- |
| **Frontend** | `app/page.tsx`, `app/layout.tsx`, `app/globals.css`, `app/icon.svg`, `components/**`, `lib/api.ts`, `lib/mock.ts`, `lib/format.ts` |
| **Backend** | `app/api/**`, `lib/server/**` |
| **Shared, locked** | `types/quest.ts`. Don't change it without telling the other side. |

Components only use the types from `types/quest.ts` and never redefine them. The one UI-only type is the wizard's form state (`components/wizard/answers.ts`), which is converted to a `QuestRequest` on submit.

### What the frontend sends (for the backend)

These are assumptions about how the form maps onto the contract. Tell the frontend if any of them don't work for you.

- **`category`**: one of `food`, `outdoors`, `arts`, `nightlife`, `games`, `surprise me`.
- **`startTime` / `endTime`**: ISO 8601 in UTC (from `Date#toISOString()`). The window is at least 30 minutes, under 24 hours, and may end the next day.
- **`budgetPerPerson`**: from the slider, 0–100 in steps of 5. **100 means "$100 or more".** Users can also type an exact amount up to 1000, which is sent literally.
- **`maxDistanceMiles`**: 1–30 from the slider, or up to 100 if typed.
- **`location`**: `{ lat, lng, label }`. `label` is a neighborhood name, `"My location"` (browser geolocation), or free text. The frontend does **no geocoding**: free text that isn't one of the built-in LA neighborhoods keeps the last known coordinates.
- **`groupSize`**: 1–20, always sent.
- **Assumption:** `Quest.totalDurationMinutes` includes travel time (time at stops plus time between them). The mock data follows that.

### How the UI is put together

```
app/page.tsx             phases: wizard → loading → results | error
components/
  TopBar, ThemeToggle    progress line, dark/light toggle (dark is the default, choice saved in localStorage)
  wizard/                one question per screen: Vibe, ClockWindow, BigRange (budget), LocationInput,
                         DistancePicker + RadiusMap, PartyStepper; EditableNumber = tap a big number to type it
  board/                 Results (selection state), QuestBoard/QuestCard (the 3 options as tabs), AnswerSummary
  detail/                QuestDetail: StopTimeline → TravelConnector + StopCard + ReviewList, RouteMap
  states/                LoadingState, ErrorState, EmptyState
lib/format.ts            money, miles, durations, times, counts: all display formatting lives here
```

- **Maps** load client-side only (`next/dynamic` with `ssr: false`). They use OpenStreetMap tiles (no API key), desaturated with CSS, and inverted in dark mode.
- **Design source:** the "Side Quest Board" file in Paper. The page "v2 — Minimal dark wizard" holds the current screens; Page 1 holds the first light-mode version.
