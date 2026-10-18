import type { Stop } from "@/types/quest";
import { formatCount, formatDuration, formatMoney, formatRating, formatTime } from "@/lib/format";
import { ReviewList } from "./ReviewList";

type Props = {
  stop: Stop;
  /** Per-person cost of this stop plus everything before it. */
  runningCost: number;
  runningIsEstimate: boolean;
  isLast: boolean;
};

export function StopCard({ stop, runningCost, runningIsEstimate, isLast }: Props) {
  const when = [stop.startTime ? formatTime(stop.startTime) : null, formatDuration(stop.durationMinutes)]
    .filter(Boolean)
    .join(" · ");

  return (
    <li id={`stop-${stop.id}`} className="flex scroll-mt-24 gap-3.5">
      <div className="flex w-7 shrink-0 flex-col items-center" aria-hidden>
        <span className="flex size-7 items-center justify-center rounded-full bg-sign font-display text-sm font-extrabold text-on-sign">
          {stop.order}
        </span>
        {!isLast && <span className="w-0.5 flex-1 bg-line" />}
      </div>

      <div className={`flex min-w-0 flex-1 flex-col gap-2.5 ${isLast ? "pb-2" : "pb-5"}`}>
        <div className="flex items-start justify-between gap-3">
          <span className="pt-0.5 text-[13px] font-medium text-muted">{when}</span>
          <div className="flex flex-col items-end">
            <div className="flex items-baseline gap-1.5">
              {stop.costIsEstimate && stop.estimatedCost > 0 && (
                <span className="rounded-full border border-line px-1.5 py-px text-[11px] font-medium text-muted">estimate</span>
              )}
              <span className="font-display text-lg font-extrabold">
                {formatMoney(stop.estimatedCost, { estimate: stop.costIsEstimate })}
              </span>
            </div>
            {stop.order > 1 && (
              <span className="text-[11px] text-muted">{formatMoney(runningCost, { estimate: runningIsEstimate })} so far</span>
            )}
          </div>
        </div>

        <div className="flex flex-col gap-0.5">
          <h3 className="font-display text-xl leading-6 font-extrabold tracking-[-0.02em]">{stop.name}</h3>
          <p className="text-[13px] leading-[18px] text-muted">
            {stop.category} · {stop.address}
          </p>
        </div>

        {stop.rating !== undefined && (
          <div className="flex items-center gap-1.5 text-[13px]">
            <svg width="14" height="14" viewBox="0 0 24 24" className="fill-sign" aria-hidden>
              <path d="M12 2l3 7 7 .6-5.3 4.7 1.6 7.2L12 17.8 5.7 21.5l1.6-7.2L2 9.6 9 9z" />
            </svg>
            <span className="font-semibold">{formatRating(stop.rating)}</span>
            {stop.reviewCount !== undefined && (
              <span className="text-muted">({formatCount(stop.reviewCount)} reviews)</span>
            )}
          </div>
        )}

        <p className="text-sm leading-[21px]">{stop.reviewSummary}</p>

        <div className="flex flex-wrap items-start gap-x-5 gap-y-2">
          <ReviewList reviews={stop.reviews} stopName={stop.name} />
          {stop.sourceUrl && (
            <a
              href={stop.sourceUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[13px] font-medium text-muted underline underline-offset-2 transition hover:text-text"
            >
              Details ↗
            </a>
          )}
        </div>
      </div>
    </li>
  );
}
