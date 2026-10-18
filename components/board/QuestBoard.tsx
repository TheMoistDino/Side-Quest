"use client";

import { useRef } from "react";
import type { Quest } from "@/types/quest";
import { QuestCard } from "./QuestCard";

type Props = {
  quests: Quest[];
  selectedId: string;
  onSelect: (id: string) => void;
  panelId: string;
};

export function QuestBoard({ quests, selectedId, onSelect, panelId }: Props) {
  const listRef = useRef<HTMLDivElement>(null);

  // Arrow keys move between tabs (WAI-ARIA tabs pattern).
  function handleKeyDown(e: React.KeyboardEvent<HTMLButtonElement>, index: number) {
    const delta = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const next = quests[(index + delta + quests.length) % quests.length];
    onSelect(next.id);
    const tab = listRef.current?.querySelector<HTMLButtonElement>(`#quest-tab-${CSS.escape(next.id)}`);
    tab?.focus();
    tab?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  }

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col">
          <h2 className="font-display text-[40px] leading-[42px] font-extrabold tracking-tight">
            {quests.length} {quests.length === 1 ? "quest" : "quests"} pinned
          </h2>
        </div>
        <span className="hidden pb-1 text-sm text-muted md:block">Pick one to see the route</span>
      </div>
      <div
        ref={listRef}
        role="tablist"
        aria-label="Quest options"
        className="-mx-6 flex snap-x snap-mandatory scroll-px-6 gap-3 overflow-x-auto px-6 pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:mx-0 md:overflow-visible md:px-0"
      >
        {quests.map((q, i) => (
          <QuestCard
            key={q.id}
            quest={q}
            index={i}
            selected={q.id === selectedId}
            panelId={panelId}
            onSelect={() => onSelect(q.id)}
            onKeyDown={(e) => handleKeyDown(e, i)}
          />
        ))}
      </div>
    </div>
  );
}
