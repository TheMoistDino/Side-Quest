type Props = {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
};

export function GroupSizeStepper({ value, onChange, min = 1, max = 12 }: Props) {
  const btn =
    "flex h-9 w-10 items-center justify-center text-lg font-semibold disabled:text-line";
  return (
    <div className="flex items-center justify-between">
      <span id="group-size-label" className="text-[15px] font-semibold">
        Party size
      </span>
      <div role="group" aria-labelledby="group-size-label" className="flex items-center rounded-full border-2 border-line">
        <button type="button" className={btn} aria-label="Fewer people" disabled={value <= min} onClick={() => onChange(value - 1)}>
          –
        </button>
        <output aria-live="polite" className="w-8 text-center font-display text-lg font-extrabold">
          {value}
        </output>
        <button type="button" className={btn} aria-label="More people" disabled={value >= max} onClick={() => onChange(value + 1)}>
          +
        </button>
      </div>
    </div>
  );
}
