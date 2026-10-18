"use client";

import { useEffect, useState } from "react";

const MESSAGES = [
  "Scouting spots…",
  "Checking reviews…",
  "Counting the cost…",
  "Plotting the route…",
  "Asking the locals…",
];

type Props = { locationLabel?: string };

export function LoadingState({ locationLabel }: Props) {
  const [i, setI] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setI((n) => (n + 1) % MESSAGES.length), 1200);
    return () => clearInterval(id);
  }, []);

  return (
    <div role="status" aria-live="polite" className="flex flex-1 flex-col justify-center gap-6 py-10">
      <div className="flex gap-2" aria-hidden>
        {[0, 1, 2].map((n) => (
          <span key={n} className="size-2.5 animate-pulse-dot rounded-full bg-sign" style={{ animationDelay: `${n * 0.18}s` }} />
        ))}
      </div>
      <div className="flex flex-col gap-2.5">
        <p key={i} className="animate-rise font-display text-[40px] leading-[42px] font-extrabold tracking-tight">
          {MESSAGES[i]}
        </p>
        <p className="text-[15px] text-muted">Plotting a few routes near {locationLabel || "you"}</p>
      </div>
    </div>
  );
}
