import type { Quest } from "@/types/quest";
import { formatDuration, formatMiles, formatMoney } from "@/lib/format";
import { StatBlock } from "./StatBlock";

type Props = {
  quest: Quest;
  index: number;
  selected: boolean;
  panelId: string;
  onSelect: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLButtonElement>) => void;
};

export function QuestCard({ quest, index, selected, panelId, onSelect, onKeyDown }: Props) {
  const hasEstimate = quest.stops.some((s) => s.costIsEstimate);
  const soft = selected ? "text-on-sign/70" : "text-muted";
  return (
    <button
      type="button"
      role="tab"
      id={`quest-tab-${quest.id}`}
      aria-selected={selected}
      aria-controls={panelId}
      tabIndex={selected ? 0 : -1}
      onClick={onSelect}
      onKeyDown={onKeyDown}
      className={[
        "flex w-[80%] shrink-0 snap-start flex-col gap-4 rounded-2xl border p-5 text-left transition md:w-auto md:flex-1 md:shrink",
        selected ? "border-sign bg-sign text-on-sign" : "border-line hover:border-muted",
      ].join(" ")}
    >
      <span className={`whitespace-nowrap text-[13px] font-medium ${soft}`}>
        Quest {index + 1} · {quest.stops.length} stops
      </span>
      <div className="flex flex-col gap-1.5">
        <h3 className="font-display text-[22px] leading-6 font-extrabold tracking-[-0.02em]">{quest.title}</h3>
        <p className={`text-sm leading-5 ${soft}`}>{quest.tagline}</p>
      </div>
      <div className={`mt-auto flex justify-between gap-2 border-t pt-3.5 ${selected ? "border-on-sign/15" : "border-line"}`}>
        <StatBlock value={formatMoney(quest.totalCostPerPerson, { estimate: hasEstimate })} label="per person" labelClass={soft} />
        <StatBlock value={formatDuration(quest.totalDurationMinutes, { compact: true })} label="total" labelClass={soft} />
        <StatBlock value={formatMiles(quest.totalDistanceMiles)} label="travel" labelClass={soft} />
      </div>
    </button>
  );
}
