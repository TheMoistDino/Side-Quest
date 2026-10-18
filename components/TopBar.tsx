import { ThemeToggle } from "./ThemeToggle";

type Props = {
  /** 0-based step and total; omit to hide the progress line. */
  progress?: { step: number; total: number };
  onHome?: () => void;
};

export function TopBar({ progress, onHome }: Props) {
  return (
    <header className="flex flex-col gap-5 pt-6">
      <div className="flex items-center justify-between">
        <button type="button" onClick={onHome} disabled={!onHome} className="text-[13px] font-medium text-muted transition enabled:hover:text-text">
          Side Quest
        </button>
        <div className="flex items-center gap-3">
          {progress && (
            <span className="text-[13px] font-medium text-muted tabular-nums">
              {progress.step + 1} / {progress.total}
            </span>
          )}
          <ThemeToggle />
        </div>
      </div>
      {progress && (
        <div
          role="progressbar"
          aria-label="Progress"
          aria-valuemin={1}
          aria-valuemax={progress.total}
          aria-valuenow={progress.step + 1}
          className="h-0.5 overflow-hidden rounded-full bg-line"
        >
          <div
            className="h-full rounded-full bg-sign transition-[width] duration-300 ease-out"
            style={{ width: `${((progress.step + 1) / progress.total) * 100}%` }}
          />
        </div>
      )}
    </header>
  );
}
