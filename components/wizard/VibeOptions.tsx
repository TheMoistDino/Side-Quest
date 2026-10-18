export const CATEGORIES = [
  { value: "food", label: "Food" },
  { value: "outdoors", label: "Outdoors" },
  { value: "arts", label: "Arts" },
  { value: "nightlife", label: "Nightlife" },
  { value: "games", label: "Games" },
  { value: "surprise me", label: "Surprise me" },
] as const;

export function categoryLabel(value: string) {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

type Props = {
  value: string;
  onPick: (value: string) => void;
};

export function VibeOptions({ value, onPick }: Props) {
  return (
    <div role="radiogroup" aria-label="Vibe" className="flex flex-col gap-2">
      {CATEGORIES.map((c) => {
        const selected = c.value === value;
        return (
          <button
            key={c.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onPick(c.value)}
            className={[
              "flex items-center justify-between rounded-xl border px-[18px] py-4 text-left text-base transition",
              selected
                ? "border-sign bg-sign font-semibold text-on-sign"
                : "border-line font-medium hover:border-muted",
              c.value === "surprise me" && !selected ? "text-muted" : "",
            ].join(" ")}
          >
            {c.label}
            {selected && (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M5 12l5 5 9-10" />
              </svg>
            )}
          </button>
        );
      })}
    </div>
  );
}
