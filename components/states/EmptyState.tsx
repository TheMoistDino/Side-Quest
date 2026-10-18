type Props =
  | { variant: "idle" }
  | { variant: "no-results"; onRetry: () => void };

export function EmptyState(props: Props) {
  const idle = props.variant === "idle";
  return (
    <div className="flex min-h-80 flex-col items-center justify-center gap-4 rounded-2xl border-2 border-dashed border-line p-8 text-center">
      <svg width="56" height="56" viewBox="0 0 56 56" fill="none" aria-hidden>
        <rect x="25" y="20" width="6" height="32" rx="2" fill="var(--color-ink)" />
        <path d="M10 8h30l6 7-6 7H10z" fill="var(--color-sign)" stroke="var(--color-ink)" strokeWidth="2.5" strokeLinejoin="round" transform="rotate(-4 28 15)" />
      </svg>
      <h2 className="font-display text-[26px] font-extrabold tracking-tight">
        {idle ? "The board is empty… for now" : "No quests in range"}
      </h2>
      <p className="max-w-sm text-[15px] text-muted">
        {idle
          ? "Pick a vibe and a time window, and we'll pin a few side quests here."
          : "Nothing fit those settings. Try a bigger budget, a longer window, or a wider radius."}
      </p>
      {!idle && (
        <button type="button" onClick={props.onRetry} className="rounded-lg border-2 border-ink px-4 py-2.5 text-[15px] font-bold transition hover:bg-fog">
          Search again
        </button>
      )}
    </div>
  );
}
