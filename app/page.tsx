"use client";

import { useEffect, useRef, useState } from "react";
import type { QuestResponse } from "@/types/quest";
import { generateQuests, QuestApiError } from "@/lib/api";
import { TopBar } from "@/components/TopBar";
import { Wizard, STEP_COUNT } from "@/components/wizard/Wizard";
import { INITIAL_ANSWERS, defaultWindow, toQuestRequest, type Answers } from "@/components/wizard/answers";
import { LoadingState } from "@/components/states/LoadingState";
import { ErrorState } from "@/components/states/ErrorState";
import { EmptyState } from "@/components/states/EmptyState";
import { AnswerSummary } from "@/components/board/AnswerSummary";
import { Results } from "@/components/board/Results";

type Phase =
  | { kind: "wizard"; step: number }
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "results"; data: QuestResponse };

export default function Home() {
  const [phase, setPhase] = useState<Phase>({ kind: "wizard", step: 0 });
  const [answers, setAnswers] = useState<Answers>(INITIAL_ANSWERS);
  const requestId = useRef(0);

  // Default time window depends on the viewer's clock and time zone, so set it after mount.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAnswers((a) => (a.start ? a : { ...a, ...defaultWindow() }));
  }, []);

  const screen = phase.kind === "wizard" ? `step-${phase.step}` : phase.kind;
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [screen]);

  async function search() {
    const id = ++requestId.current;
    setPhase({ kind: "loading" });
    try {
      const data = await generateQuests(toQuestRequest(answers));
      if (id === requestId.current) setPhase({ kind: "results", data });
    } catch (err) {
      if (id !== requestId.current) return;
      const message = err instanceof QuestApiError ? err.message : "Something went wrong. Please try again.";
      setPhase({ kind: "error", message });
    }
  }

  const goToStep = (step: number) => {
    requestId.current++; // drop any in-flight response
    setPhase({ kind: "wizard", step });
  };

  const wide = phase.kind === "results";

  return (
    <div className={`mx-auto flex min-h-dvh w-full flex-col px-6 ${wide ? "max-w-5xl" : "max-w-xl"}`}>
      <TopBar
        progress={phase.kind === "wizard" ? { step: phase.step, total: STEP_COUNT } : undefined}
        onHome={phase.kind === "wizard" && phase.step === 0 ? undefined : () => goToStep(0)}
      />

      <main className="flex flex-1 flex-col pb-6">
        {phase.kind === "wizard" && (
          <Wizard
            step={phase.step}
            answers={answers}
            onChange={(patch) => setAnswers((a) => ({ ...a, ...patch }))}
            onStep={goToStep}
            onSubmit={search}
          />
        )}

        {phase.kind === "loading" && <LoadingState locationLabel={answers.location.label} />}

        {phase.kind === "error" && (
          <ErrorState message={phase.message} onRetry={search} onEdit={() => goToStep(STEP_COUNT - 1)} />
        )}

        {phase.kind === "results" && (
          <div className="flex animate-rise flex-col gap-8 py-10">
            <AnswerSummary answers={answers} onEdit={goToStep} />
            {phase.data.quests.length === 0 ? (
              <EmptyState onEdit={() => goToStep(2)} />
            ) : (
              <Results quests={phase.data.quests} />
            )}
          </div>
        )}
      </main>
    </div>
  );
}
