import { EditableNumber } from "./EditableNumber";

type Props = {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  /** User tried to go past `max` (typed or tapped +). */
  onOverflow?: () => void;
};

export function PartyStepper({ value, onChange, min = 1, max = 20, onOverflow }: Props) {
  const btn =
    "flex size-14 items-center justify-center rounded-full border border-line text-2xl font-medium transition enabled:hover:border-muted disabled:opacity-30";
  return (
    <div role="group" aria-label="Party size" className="flex items-center justify-center gap-8">
      <button type="button" className={btn} aria-label="Fewer people" disabled={value <= min} onClick={() => onChange(value - 1)}>
        –
      </button>
      <div className="min-w-[2ch] text-center" aria-live="polite">
        <EditableNumber
          label="Party size"
          value={value}
          min={min}
          max={max}
          onChange={onChange}
          format={String}
          onOverflow={onOverflow}
          className="font-display text-[88px] leading-[96px] font-extrabold tracking-[-0.04em] text-sign-ink tabular-nums"
        />
      </div>
      <button
        type="button"
        className={`${btn} ${value >= max ? "opacity-30" : ""}`}
        aria-label="More people"
        onClick={() => (value >= max ? onOverflow?.() : onChange(value + 1))}
      >
        +
      </button>
    </div>
  );
}
