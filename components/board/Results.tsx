"use client";

import { useState } from "react";
import type { Quest, QuestRequest } from "@/types/quest";
import { QuestDetail } from "@/components/detail/QuestDetail";
import { QuestBoard } from "./QuestBoard";

const PANEL_ID = "quest-detail";

type Props = { quests: Quest[]; origin: QuestRequest["location"] };

export function Results({ quests, origin }: Props) {
  const [selectedId, setSelectedId] = useState(quests[0].id);
  const selected = quests.find((q) => q.id === selectedId) ?? quests[0];

  return (
    <div className="flex flex-col gap-10">
      <QuestBoard quests={quests} selectedId={selected.id} onSelect={setSelectedId} panelId={PANEL_ID} />
      <div id={PANEL_ID} role="tabpanel" aria-labelledby={`quest-tab-${selected.id}`}>
        {/* Keyed so expanded reviews reset when switching quests. */}
        <QuestDetail key={selected.id} quest={selected} origin={origin} />
      </div>
    </div>
  );
}
