"use client";

import dynamic from "next/dynamic";
import type { Quest, QuestRequest } from "@/types/quest";
import { formatDuration, formatMiles, formatMoney } from "@/lib/format";
import { StatBlock } from "@/components/board/StatBlock";
import { StopTimeline } from "./StopTimeline";

// Leaflet touches `window`, so the map only renders in the browser.
const RouteMap = dynamic(() => import("./RouteMap"), {
  ssr: false,
  loading: () => <div className="size-full animate-pulse bg-surface" />,
});

type Props = {
  quest: Quest;
  origin: QuestRequest["location"];
};

export function QuestDetail({ quest, origin }: Props) {
  const hasEstimate = quest.stops.some((s) => s.costIsEstimate);
  const total = formatMoney(quest.totalCostPerPerson, { estimate: hasEstimate });

  function scrollToStop(id: string) {
    document.getElementById(`stop-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // One grid, one map: on mobile the map sits between header and timeline;
  // on desktop it spans the right column and sticks while the timeline scrolls.
  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:gap-x-10">
      <header className="flex flex-col gap-2 lg:col-start-1 lg:row-start-1">
        <span className="text-[13px] font-medium text-muted">The route</span>
        <h2 className="font-display text-[28px] leading-[30px] font-extrabold tracking-tight">{quest.title}</h2>
        <div className="flex flex-wrap gap-x-5 gap-y-2 pt-1">
          <div className="flex flex-col whitespace-nowrap">
            <span className="font-display text-lg leading-6 font-extrabold text-sign-ink">{total}</span>
            <span className="text-xs text-muted">per person</span>
          </div>
          <StatBlock value={formatDuration(quest.totalDurationMinutes, { compact: true })} label="total" />
          <StatBlock value={formatDuration(quest.totalTravelMinutes, { compact: true })} label="travel" />
          <StatBlock value={formatMiles(quest.totalDistanceMiles)} label="distance" />
        </div>
      </header>

      <div className="h-60 self-start overflow-hidden rounded-2xl border border-line bg-surface lg:sticky lg:top-6 lg:col-start-2 lg:row-span-3 lg:row-start-1 lg:h-[520px]">
        <RouteMap stops={quest.stops} origin={origin} onStopClick={(s) => scrollToStop(s.id)} />
      </div>

      <div className="lg:col-start-1 lg:row-start-2">
        <StopTimeline stops={quest.stops} origin={origin} />
      </div>

      <div className="flex items-center justify-between self-start rounded-2xl border border-line px-[18px] py-4 lg:col-start-1 lg:row-start-3">
        <div className="flex flex-col gap-0.5">
          <span className="text-xs text-muted">Total per person</span>
          <span className="font-display text-2xl font-extrabold text-sign-ink">{total}</span>
        </div>
        <div className="flex flex-col items-end gap-0.5">
          <span className="text-xs text-muted">Time on the road</span>
          <span className="font-display text-2xl font-extrabold">{formatDuration(quest.totalTravelMinutes)}</span>
        </div>
      </div>
    </div>
  );
}
