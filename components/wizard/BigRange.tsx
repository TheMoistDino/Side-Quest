import { EditableNumber } from "./EditableNumber";

type Props = {
  label: string;
  min: number;
  max: number;
  /** Typing can go past the slider's end, up to this. Defaults to `max`. */
  typedMax?: number;
  increment?: number;
  value: number;
  onChange: (value: number) => void;
  format: (value: number) => string;
  prefix?: string;
  suffix?: string;
};

export function BigRange({ label, min, max, typedMax = max, increment = 1, value, onChange, format, prefix, suffix }: Props) {
  const sliderValue = Math.min(value, max);
  const fill = `${((sliderValue - min) / (max - min)) * 100}%`;
  return (
    <div className="flex flex-col gap-7">
      <div>
        <EditableNumber
          label={label}
          value={value}
          min={min}
          max={typedMax}
          onChange={onChange}
          format={format}
          prefix={prefix}
          suffix={suffix}
          className="font-display text-[88px] leading-[96px] font-extrabold tracking-[-0.04em] text-sign-ink tabular-nums"
        />
      </div>
      <input
        type="range"
        aria-label={label}
        min={min}
        max={max}
        step={increment}
        value={sliderValue}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-valuetext={format(value)}
        className="quest-range"
        style={{ "--fill": fill } as React.CSSProperties}
      />
      <div className="flex justify-between text-[13px] text-muted">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}
