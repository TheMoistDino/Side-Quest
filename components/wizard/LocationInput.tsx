"use client";

import { useState } from "react";
import type { QuestRequest } from "@/types/quest";

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

export const MY_LOCATION_LABEL = "My location";

type GeoStatus = "idle" | "locating" | "denied";

type Props = {
  value: Location;
  onChange: (value: Location) => void;
};

const findPreset = (label = "") => PRESETS.find((p) => p.label.toLowerCase() === label.trim().toLowerCase());

export function LocationInput({ value, onChange }: Props) {
  const [geo, setGeo] = useState<GeoStatus>("idle");
  const usingDevice = value.label === MY_LOCATION_LABEL;
  const unknown = !findPreset(value.label) && !usingDevice && (value.label ?? "").trim() !== "";

  function handleText(label: string) {
    const match = findPreset(label);
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
        onChange({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: MY_LOCATION_LABEL });
      },
      () => setGeo("denied"),
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  }

  return (
    <div className="flex flex-col gap-3">
      <input
        aria-label="Starting neighborhood"
        list="location-presets"
        value={value.label ?? ""}
        onChange={(e) => handleText(e.target.value)}
        onFocus={(e) => {
          if (usingDevice) e.target.select();
        }}
        placeholder="Neighborhood"
        className="w-full rounded-xl border border-line bg-transparent px-[18px] py-4 text-base font-semibold outline-none transition focus:border-muted"
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
          "flex items-center justify-center gap-2 rounded-xl border px-[18px] py-4 text-base font-medium transition",
          usingDevice ? "border-sign bg-sign font-semibold text-on-sign" : "border-line hover:border-muted",
        ].join(" ")}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden className={geo === "locating" ? "animate-spin" : ""}>
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
        </svg>
        {geo === "locating" ? "Finding you…" : usingDevice ? "Using your location" : "Use my location"}
      </button>
      <p className="min-h-5 text-sm text-muted" aria-live="polite">
        {geo === "denied"
          ? "Couldn't get your location. Pick a neighborhood instead."
          : unknown
            ? "We don't know that spot yet, so we'll search near your last location."
            : ""}
      </p>
    </div>
  );
}
