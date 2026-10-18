type Props = {
  title: string;
  hint?: string;
  children: React.ReactNode;
  onBack?: () => void;
  onNext: () => void;
  nextLabel?: string;
  canContinue?: boolean;
  /** Tiny line shown just above Back / Continue. */
  footnote?: React.ReactNode;
};

export function StepFrame({ title, hint, children, onBack, onNext, nextLabel = "Continue", canContinue = true, footnote }: Props) {
  return (
    <form
      className="flex flex-1 flex-col"
      onSubmit={(e) => {
        e.preventDefault();
        if (canContinue) onNext();
      }}
    >
      <div className="flex flex-1 flex-col justify-center gap-10 py-10">
        <div className="flex animate-rise flex-col gap-2.5">
          <h1 className="font-display text-[40px] leading-[42px] font-extrabold tracking-tight sm:text-5xl sm:leading-[52px]">
            {title}
          </h1>
          {hint && <p className="text-[15px] leading-[22px] text-muted">{hint}</p>}
        </div>
        <div className="animate-rise [animation-delay:60ms]">{children}</div>
      </div>

      <p aria-live="polite" className="min-h-4 pb-3 text-center text-xs text-muted">
        {footnote && <span key={String(footnote)} className="inline-block animate-rise">{footnote}</span>}
      </p>
      <div className="flex items-center justify-between pb-2">
        <button
          type="button"
          onClick={onBack}
          disabled={!onBack}
          className="-ml-2 rounded-full px-2 py-2 text-[15px] font-medium transition enabled:hover:text-muted disabled:opacity-30"
        >
          Back
        </button>
        <button
          type="submit"
          disabled={!canContinue}
          className="group flex items-center gap-2 rounded-full bg-sign px-[22px] py-3.5 text-[15px] font-semibold text-on-sign transition enabled:hover:brightness-105 enabled:active:scale-[0.98] disabled:opacity-40"
        >
          {nextLabel}
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="transition group-enabled:group-hover:translate-x-0.5">
            <path d="M5 12h14M13 6l6 6-6 6" />
          </svg>
        </button>
      </div>
    </form>
  );
}
