export const CATEGORIES = [
  { value: "food", label: "Food" },
  { value: "outdoors", label: "Outdoors" },
  { value: "arts", label: "Arts" },
  { value: "nightlife", label: "Nightlife" },
  { value: "games", label: "Games" },
  { value: "surprise me", label: "Surprise me" },
] as const;

type Props = {
  value: string;
  onChange: (value: string) => void;
};

export function CategoryPicker({ value, onChange }: Props) {
  return (
    <div role="radiogroup" aria-label="Category" className="flex flex-wrap gap-2">
      {CATEGORIES.map((c) => {
        const selected = c.value === value;
        const surprise = c.value === "surprise me";
        return (
          <button
            key={c.value}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(c.value)}
            className={[
              "rounded-full border-2 px-3.5 py-2 text-sm font-semibold transition",
              selected
                ? "border-ink bg-sign shadow-hard-sm"
                : surprise
                  ? "border-dashed border-ink hover:bg-fog"
                  : "border-line hover:border-ink",
            ].join(" ")}
          >
            {c.label}
          </button>
        );
      })}
    </div>
  );
}
