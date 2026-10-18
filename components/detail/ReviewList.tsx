"use client";

import { useState } from "react";
import type { Review } from "@/types/quest";

type Props = { reviews: Review[]; stopName: string };

export function ReviewList({ reviews, stopName }: Props) {
  const [open, setOpen] = useState(false);
  if (reviews.length === 0) return null;

  const id = `reviews-${stopName.replace(/\W+/g, "-").toLowerCase()}`;
  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="self-start text-[13px] font-semibold transition hover:text-muted"
      >
        {open ? "Hide reviews ↑" : `Read ${reviews.length} ${reviews.length === 1 ? "review" : "reviews"} ↓`}
      </button>
      {open && (
        <ul id={id} className="flex animate-rise flex-col gap-1.5">
          {reviews.map((r, i) => (
            <li key={i} className="flex flex-col gap-1.5 rounded-xl bg-surface px-3.5 py-3">
              <p className="text-[13px] leading-[19px]">&ldquo;{r.snippet}&rdquo;</p>
              <div className="flex items-center justify-between gap-3 text-xs">
                <span className="text-muted">
                  {[r.rating !== undefined ? `★ ${r.rating}` : null, r.author].filter(Boolean).join(" · ")}
                </span>
                <a
                  href={r.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 font-medium underline underline-offset-2 transition hover:text-muted"
                >
                  {r.sourceName} ↗
                </a>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
