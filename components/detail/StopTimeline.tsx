import { Fragment } from "react";
import type { QuestRequest, Stop } from "@/types/quest";
import { StopCard } from "./StopCard";
import { TravelConnector } from "./TravelConnector";

type Props = {
  stops: Stop[];
  origin: QuestRequest["location"];
};

export function StopTimeline({ stops, origin }: Props) {
  const ordered = [...stops].sort((a, b) => a.order - b.order);
  // Running per-person cost after each stop, and whether any part of it is an estimate.
  const running = ordered.map((_, i) => {
    const upTo = ordered.slice(0, i + 1);
    return {
      cost: upTo.reduce((sum, s) => sum + s.estimatedCost, 0),
      isEstimate: upTo.some((s) => s.costIsEstimate),
    };
  });

  // "Westwood, Los Angeles" → "Westwood" keeps the first connector on one line.
  const shortLabel = origin.label?.split(",")[0].trim() || "your location";

  return (
    <ol aria-label="Stops in order" className="flex flex-col">
      {ordered.map((stop, i) => (
        <Fragment key={stop.id}>
          <TravelConnector stop={stop} fromLabel={i === 0 ? shortLabel : undefined} />
          <StopCard
            stop={stop}
            runningCost={running[i].cost}
            runningIsEstimate={running[i].isEstimate}
            isLast={i === ordered.length - 1}
          />
        </Fragment>
      ))}
    </ol>
  );
}
