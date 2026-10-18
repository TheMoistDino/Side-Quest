"use client";

import { useRef, useState } from "react";
import type { QuestRequest, QuestResponse } from "@/types/quest";
import { generateQuests, QuestApiError } from "@/lib/api";
import { QuestForm } from "@/components/form/QuestForm";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { EmptyState } from "@/components/states/EmptyState";

type Status =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "success"; data: QuestResponse };

export default function Home() {
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [lastRequest, setLastRequest] = useState<QuestRequest | null>(null);
  const requestId = useRef(0);
  const resultsRef = useRef<HTMLElement>(null);

  async function run(req: QuestRequest) {
    const id = ++requestId.current;
    setLastRequest(req);
    setStatus({ kind: "loading" });
    if (window.matchMedia("(max-width: 1023px)").matches) {
      resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    try {
      const data = await generateQuests(req);
      if (id === requestId.current) setStatus({ kind: "success", data });
    } catch (err) {
      if (id !== requestId.current) return;
      const message = err instanceof QuestApiError ? err.message : "Something went wrong. Please try again.";
      setStatus({ kind: "error", message });
    }
  }

  const retry = () => lastRequest && run(lastRequest);

  return (
    <main className="mx-auto flex w-full max-w-7xl flex-col gap-10 px-5 py-7 lg:flex-row lg:gap-12 lg:px-8 lg:py-10">
      <aside className="flex w-full flex-col gap-7 lg:sticky lg:top-10 lg:w-[420px] lg:shrink-0 lg:self-start">
        <header className="flex flex-col gap-2.5">
          <div className="flex items-center gap-2">
            <span className="size-[22px] -rotate-[8deg] rounded-md border-2 border-ink bg-sign" aria-hidden />
            <span className="text-xs font-bold uppercase tracking-caps">Side Quest Board</span>
          </div>
          <h1 className="font-display text-[44px] font-extrabold leading-[44px] tracking-tight">
            Got free time?
            <br />
            Pick a quest.
          </h1>
          <p className="text-[15px] leading-[22px] text-muted">
            Tell us your window and budget. We&apos;ll plot a few short adventures nearby.
          </p>
        </header>
        <QuestForm onSubmit={run} busy={status.kind === "loading"} />
      </aside>

      <section ref={resultsRef} aria-label="Quest results" className="min-w-0 flex-1 scroll-mt-6">
        {status.kind === "idle" && <EmptyState variant="idle" />}
        {status.kind === "loading" && <LoadingState locationLabel={lastRequest?.location.label} />}
        {status.kind === "error" && <ErrorState message={status.message} onRetry={retry} />}
        {status.kind === "success" &&
          (status.data.quests.length === 0 ? (
            <EmptyState variant="no-results" onRetry={retry} />
          ) : (
            // Temporary until the Board lands in step 3.
            <ul className="flex flex-col gap-3">
              {status.data.quests.map((q) => (
                <li key={q.id} className="rounded-2xl border-2 border-ink p-5">
                  <p className="font-display text-2xl font-extrabold tracking-tight">{q.title}</p>
                  <p className="text-[15px] text-muted">{q.tagline}</p>
                </li>
              ))}
            </ul>
          ))}
      </section>
    </main>
  );
}
