import { FieldLabel } from "./FieldLabel";

type Props = {
  start: string; // datetime-local value
  end: string;
  onStartChange: (value: string) => void;
  onEndChange: (value: string) => void;
  error?: string;
};

const boxClass =
  "flex min-w-0 items-center justify-between gap-3 rounded-lg border-2 border-line px-3 py-2.5 focus-within:border-ink";

export function TimeWindowField({ start, end, onStartChange, onEndChange, error }: Props) {
  return (
    <div className="flex flex-col gap-2.5">
      <FieldLabel step={2}>Time window</FieldLabel>
      <div className="flex flex-col gap-2">
        <label className={boxClass}>
          <span className="shrink-0 text-sm text-muted">Leave</span>
          <input
            type="datetime-local"
            value={start}
            onChange={(e) => onStartChange(e.target.value)}
            className="min-w-0 bg-transparent text-right text-[15px] font-semibold outline-none"
            required
          />
        </label>
        <label className={boxClass}>
          <span className="shrink-0 text-sm text-muted">Back by</span>
          <input
            type="datetime-local"
            value={end}
            min={start}
            onChange={(e) => onEndChange(e.target.value)}
            className="min-w-0 bg-transparent text-right text-[15px] font-semibold outline-none"
            required
          />
        </label>
      </div>
      {error && <p className="text-sm font-medium text-danger">{error}</p>}
    </div>
  );
}
