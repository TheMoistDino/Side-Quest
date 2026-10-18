"use client";

import { useState } from "react";
import type { Quest } from "@/types/quest";
import { QuestBoard } from "./QuestBoard";

const PANEL_ID = "quest-detail";

type Props = { quests: Quest[] };

export function Results({ quests }: Props) {
  const [selectedId, setSelectedId] = useState(quests[0].id);
  const selected = quests.find((q) => q.id === selectedId) ?? quests[0];

  return (
    <div className="flex flex-col gap-8">
      <QuestBoard quests={quests} selectedId={selected.id} onSelect={setSelectedId} panelId={PANEL_ID} />
      <div id={PANEL_ID} role="tabpanel" aria-labelledby={`quest-tab-${selected.id}`}>
        {/* Step 4: timeline + map for `selected` goes here. */}
        <ol className="flex flex-col gap-2 rounded-2xl border border-line p-5 text-[15px]">
          {selected.stops.map((s) => (
            <li key={s.id}>
              <span className="font-display font-extrabold">{s.order}.</span> {s.name}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
