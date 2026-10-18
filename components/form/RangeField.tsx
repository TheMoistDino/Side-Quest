import { FieldLabel } from "./FieldLabel";

type Props = {
  id: string;
  step: number;
  label: string;
  min: number;
  max: number;
  increment?: number;
  value: number;
  onChange: (value: number) => void;
  format: (value: number) => string;
};

export function RangeField({ id, step, label, min, max, increment = 1, value, onChange, format }: Props) {
  const fill = `${((value - min) / (max - min)) * 100}%`;
  return (
    <div className="flex flex-col gap-3">
      <FieldLabel step={step} htmlFor={id} value={format(value)}>
        {label}
      </FieldLabel>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={increment}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-valuetext={format(value)}
        className="quest-range"
        style={{ "--fill": fill } as React.CSSProperties}
      />
      <div className="flex justify-between text-xs text-muted">
        <span>{format(min)}</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}
