"use client";

import dynamic from "next/dynamic";
import type { QuestRequest } from "@/types/quest";
import { EditableNumber } from "./EditableNumber";

// Leaflet touches `window`, so the map only renders in the browser.
const RadiusMap = dynamic(() => import("./RadiusMap"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-surface" />,
});

const MIN = 1;
const MAX = 30;
const TYPED_MAX = 100;

type Props = {
  value: number;
  onChange: (value: number) => void;
  location: QuestRequest["location"];
};

export function DistancePicker({ value, onChange, location }: Props) {
  const sliderValue = Math.min(value, MAX);
  const fill = `${((sliderValue - MIN) / (MAX - MIN)) * 100}%`;
  return (
    <div className="flex flex-col gap-5">
      <div className="h-[220px] overflow-hidden rounded-2xl border border-line bg-surface">
        <RadiusMap lat={location.lat} lng={location.lng} radiusMiles={value} />
      </div>
      <div className="flex items-baseline gap-2.5">
        <EditableNumber
          label="Max distance in miles"
          value={value}
          min={MIN}
          max={TYPED_MAX}
          onChange={onChange}
          format={(v) => `${v} mi`}
          suffix=" mi"
          className="font-display text-[56px] leading-[64px] font-extrabold tracking-[-0.04em] text-sign tabular-nums"
        />
        <span className="text-sm text-muted">radius</span>
      </div>
      <input
        type="range"
        aria-label="Max distance in miles"
        min={MIN}
        max={MAX}
        value={sliderValue}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-valuetext={`${value} miles`}
        className="quest-range"
        style={{ "--fill": fill } as React.CSSProperties}
      />
      <div className="flex justify-between text-[13px] text-muted">
        <span>{MIN} mi</span>
        <span>{MAX} mi</span>
      </div>
    </div>
  );
}
