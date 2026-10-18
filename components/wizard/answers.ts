import type { QuestRequest } from "@/types/quest";
import { toDateTimeLocal } from "@/lib/format";

// UI-only form state. Converted to the shared QuestRequest contract on submit.
export type Answers = {
  category: string;
  start: string; // datetime-local value, viewer's time zone
  end: string;
  budget: number;
  distance: number;
  location: QuestRequest["location"];
  groupSize: number;
};

export const DEFAULT_LOCATION: QuestRequest["location"] = {
  label: "Westwood, Los Angeles",
  lat: 34.0635,
  lng: -118.4455,
};

export const INITIAL_ANSWERS: Answers = {
  category: "",
  start: "",
  end: "",
  budget: 40,
  distance: 10,
  location: DEFAULT_LOCATION,
  groupSize: 2,
};

/** Next full hour → +5 hours. Must run on the client (depends on the viewer's clock). */
export function defaultWindow(): Pick<Answers, "start" | "end"> {
  const start = new Date();
  start.setMinutes(0, 0, 0);
  start.setHours(start.getHours() + 1);
  const end = new Date(start.getTime() + 5 * 60 * 60_000);
  return { start: toDateTimeLocal(start), end: toDateTimeLocal(end) };
}

export function toQuestRequest(a: Answers): QuestRequest {
  return {
    category: a.category,
    startTime: new Date(a.start).toISOString(),
    endTime: new Date(a.end).toISOString(),
    budgetPerPerson: a.budget,
    maxDistanceMiles: a.distance,
    location: { ...a.location, label: a.location.label?.trim() || undefined },
    groupSize: a.groupSize,
  };
}
