"use client";

import { useState } from "react";
import type { QuestRequest } from "@/types/quest";
import { FieldLabel } from "./FieldLabel";

type Location = QuestRequest["location"];

// No geocoding on the frontend (all fetching lives in lib/api.ts), so the text
// field matches a few known LA neighborhoods. Unknown text keeps the last coords.
const PRESETS: Required<Location>[] = [
  { label: "Westwood, Los Angeles", lat: 34.0635, lng: -118.4455 },
  { label: "Santa Monica", lat: 34.0195, lng: -118.4912 },
  { label: "Downtown Los Angeles", lat: 34.0407, lng: -118.2468 },
  { label: "Hollywood", lat: 34.0928, lng: -118.3287 },
  { label: "Koreatown", lat: 34.0618, lng: -118.3004 },
  { label: "Silver Lake", lat: 34.0869, lng: -118.2702 },
  { label: "Pasadena", lat: 34.1478, lng: -118.1445 },
  { label: "Long Beach", lat: 33.7701, lng: -118.1937 },
];

export const DEFAULT_LOCATION: Location = PRESETS[0];

type GeoStatus = "idle" | "locating" | "denied";

type Props = {
  value: Location;
  onChange: (value: Location) => void;
};

export function LocationField({ value, onChange }: Props) {
  const [geo, setGeo] = useState<GeoStatus>("idle");
  const preset = PRESETS.find((p) => p.label.toLowerCase() === value.label?.trim().toLowerCase());
  const usingDevice = value.label === "My location";
  const unknown = !preset && !usingDevice && (value.label ?? "").trim() !== "";

  function handleText(label: string) {
    const match = PRESETS.find((p) => p.label.toLowerCase() === label.trim().toLowerCase());
    onChange(match ? { ...match, label } : { ...value, label });
  }

  function useMyLocation() {
    if (!("geolocation" in navigator)) {
      setGeo("denied");
      return;
    }
    setGeo("locating");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGeo("idle");
        onChange({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: "My location" });
      },
      () => setGeo("denied"),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <FieldLabel step={5} htmlFor="location">
        Start from
      </FieldLabel>
      <div className="flex gap-2">
        <input
          id="location"
          list="location-presets"
          value={value.label ?? ""}
          onChange={(e) => handleText(e.target.value)}
          onFocus={(e) => usingDevice && e.target.select()}
          placeholder="Neighborhood"
          className="min-w-0 flex-1 rounded-lg border-2 border-line px-3 py-3 text-[15px] outline-none focus:border-ink"
        />
        <datalist id="location-presets">
          {PRESETS.map((p) => (
            <option key={p.label} value={p.label} />
          ))}
        </datalist>
        <button
          type="button"
          onClick={useMyLocation}
          disabled={geo === "locating"}
          className={[
            "flex shrink-0 items-center gap-1.5 rounded-lg border-2 border-ink px-3 text-sm font-semibold transition",
            usingDevice ? "bg-sign" : "hover:bg-fog",
          ].join(" ")}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" aria-hidden className={geo === "locating" ? "animate-spin" : ""}>
            <circle cx="12" cy="12" r="4" />
            <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
          </svg>
          {geo === "locating" ? "Finding…" : "Use mine"}
        </button>
      </div>
      {geo === "denied" && (
        <p className="text-sm text-muted">Couldn&apos;t get your location. Pick a neighborhood instead.</p>
      )}
      {unknown && geo !== "denied" && (
        <p className="text-sm text-muted">
          We don&apos;t know that spot yet, so we&apos;ll search near your last location. Pick a suggestion or tap
          &ldquo;Use mine&rdquo;.
        </p>
      )}
    </div>
  );
}
