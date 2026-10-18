import type { Stop } from "@/types/quest";
import { formatDuration, formatMiles } from "@/lib/format";
import { TravelModeIcon } from "./TravelModeIcon";

const MODE_WORD: Record<Stop["travelMode"], string> = {
  driving: "drive",
  walking: "walk",
  transit: "by transit",
};

type Props = {
  stop: Stop;
  /** Set for the first leg, which starts at the user's location. */
  fromLabel?: string;
};

export function TravelConnector({ stop, fromLabel }: Props) {
  const parts = [
    fromLabel ? `From ${fromLabel}` : null,
    formatMiles(stop.distanceFromPreviousMiles),
    `${formatDuration(stop.travelFromPreviousMinutes)} ${MODE_WORD[stop.travelMode]}`,
  ].filter(Boolean);

  return (
    <li className="flex gap-3.5" aria-label={`Travel: ${parts.join(", ")}`}>
      <div className="flex w-7 shrink-0 flex-col items-center" aria-hidden>
        {fromLabel && <span className="mt-1.5 size-2 rounded-full bg-text" />}
        <span className="min-h-9 flex-1 border-l-2 border-dashed border-line" />
      </div>
      <div className={`flex items-center gap-2 text-[13px] text-muted ${fromLabel ? "pb-[18px]" : "py-2 pb-4"}`}>
        <TravelModeIcon mode={stop.travelMode} />
        <span>{parts.join(" · ")}</span>
      </div>
    </li>
  );
}
