type Props = {
  message: string;
  onRetry: () => void;
};

export function ErrorState({ message, onRetry }: Props) {
  return (
    <div role="alert" className="flex min-h-80 flex-col justify-center gap-3.5 rounded-2xl border-2 border-ink p-8">
      <span className="-rotate-3 self-start rounded-full bg-danger px-2.5 py-1 text-xs font-bold uppercase tracking-caps text-white">
        Quest failed
      </span>
      <h2 className="font-display text-[26px] font-extrabold leading-[30px] tracking-tight">{message}</h2>
      <p className="text-[15px] text-muted">Please try again. Your answers are saved.</p>
      <button
        type="button"
        onClick={onRetry}
        className="self-start rounded-lg bg-ink px-4.5 py-3 text-[15px] font-bold text-white transition hover:bg-ink/85"
      >
        Try again
      </button>
    </div>
  );
}
