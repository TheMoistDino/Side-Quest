"use client";

import { useEffect, useState } from "react";

const MESSAGES = [
  "Scouting spots…",
  "Checking reviews…",
  "Counting the cost…",
  "Plotting the route…",
  "Asking the locals…",
  "Sharpening the map…",
];

type Props = { locationLabel?: string };

export function LoadingState({ locationLabel }: Props) {
  const [i, setI] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setI((n) => (n + 1) % MESSAGES.length), 1200);
    return () => clearInterval(id);
  }, []);

  return (
    <div role="status" aria-live="polite" className="flex min-h-80 flex-col items-center justify-center gap-5 rounded-2xl bg-fog p-8 text-center">
      <div className="flex items-end gap-2.5" aria-hidden>
        {[1, 2, 3].map((n) => (
          <span
            key={n}
            className={[
              "flex size-9 animate-hop items-center justify-center rounded-full border-2 border-ink font-display text-base font-extrabold",
              n === 1 ? "bg-sign" : n === 2 ? "bg-bg" : "border-dashed bg-bg text-muted",
            ].join(" ")}
            style={{ animationDelay: `${(n - 1) * 0.15}s` }}
          >
            {n}
          </span>
        ))}
      </div>
      <div className="flex flex-col gap-1.5">
        <p key={i} className="animate-rise font-display text-[26px] font-extrabold tracking-tight">
          {MESSAGES[i]}
        </p>
        <p className="text-sm text-muted">Plotting 3 routes near {locationLabel || "you"}</p>
      </div>
      <div className="relative h-1.5 w-44 overflow-hidden rounded-full bg-bg" aria-hidden>
        <div className="absolute inset-y-0 left-0 w-2/5 animate-slide rounded-full bg-ink" />
      </div>
    </div>
  );
}
