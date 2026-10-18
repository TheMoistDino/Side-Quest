"use client";

import { useEffect, useState } from "react";
import type { QuestRequest } from "@/types/quest";
import { BUDGET_MAX, formatBudget, toDateTimeLocal } from "@/lib/format";
import { CategoryPicker } from "./CategoryPicker";
import { TimeWindowField } from "./TimeWindowField";
import { RangeField } from "./RangeField";
import { LocationField, DEFAULT_LOCATION } from "./LocationField";
import { GroupSizeStepper } from "./GroupSizeStepper";

type Props = {
  onSubmit: (req: QuestRequest) => void;
  busy: boolean;
};

function defaultWindow() {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start.getTime() + 5 * 60 * 60_000);
  return { start: toDateTimeLocal(start), end: toDateTimeLocal(end) };
}

export function QuestForm({ onSubmit, busy }: Props) {
  const [category, setCategory] = useState("food");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [budget, setBudget] = useState(40);
  const [distance, setDistance] = useState(10);
  const [location, setLocation] = useState<QuestRequest["location"]>(DEFAULT_LOCATION);
  const [groupSize, setGroupSize] = useState(2);

  // Defaults depend on the viewer's clock and time zone, so set them after mount.
  useEffect(() => {
    const w = defaultWindow();
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStart(w.start);
    setEnd(w.end);
  }, []);

  const timeError = start && end && new Date(end) <= new Date(start) ? "Return time needs to be after you leave." : undefined;

  function handleStartChange(value: string) {
    // Keep the window the same length when the leave time moves.
    if (start && end && value) {
      const length = new Date(end).getTime() - new Date(start).getTime();
      setEnd(toDateTimeLocal(new Date(new Date(value).getTime() + length)));
    }
    setStart(value);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!start || !end || timeError) return;
    onSubmit({
      category,
      startTime: new Date(start).toISOString(),
      endTime: new Date(end).toISOString(),
      budgetPerPerson: budget,
      maxDistanceMiles: distance,
      location: { ...location, label: location.label?.trim() || undefined },
      groupSize,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-7">
      <div className="flex flex-col gap-2.5">
        <span className="text-xs font-bold uppercase tracking-caps">1 · Vibe</span>
        <CategoryPicker value={category} onChange={setCategory} />
      </div>

      <TimeWindowField start={start} end={end} onStartChange={handleStartChange} onEndChange={setEnd} error={timeError} />

      <RangeField
        id="budget"
        step={3}
        label="Budget per person"
        min={0}
        max={BUDGET_MAX}
        increment={5}
        value={budget}
        onChange={setBudget}
        format={formatBudget}
      />

      <RangeField
        id="distance"
        step={4}
        label="How far"
        min={1}
        max={30}
        value={distance}
        onChange={setDistance}
        format={(v) => `${v} mi`}
      />

      <div className="flex flex-col gap-4">
        <LocationField value={location} onChange={setLocation} />
        <GroupSizeStepper value={groupSize} onChange={setGroupSize} />
      </div>

      <button
        type="submit"
        disabled={busy || !start || !!timeError}
        className="group flex items-center justify-center gap-2.5 rounded-2xl border-2 border-ink bg-sign p-4 shadow-hard transition enabled:hover:-translate-y-0.5 enabled:active:translate-x-1 enabled:active:translate-y-1 enabled:active:shadow-none disabled:opacity-60"
      >
        <span className="font-display text-xl font-extrabold tracking-[-0.01em]">
          {busy ? "Scouting…" : "Find my side quest"}
        </span>
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="transition group-enabled:group-hover:translate-x-0.5">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </button>
    </form>
  );
}
