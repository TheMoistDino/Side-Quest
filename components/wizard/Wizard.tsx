"use client";

import { useRef, useState } from "react";
import { BUDGET_MAX, BUDGET_TYPED_MAX, formatBudget } from "@/lib/format";
import type { Answers } from "./answers";
import { StepFrame } from "./StepFrame";
import { VibeOptions } from "./VibeOptions";
import { ClockWindow } from "./ClockWindow";
import { BigRange } from "./BigRange";
import { LocationInput, MY_LOCATION_LABEL } from "./LocationInput";
import { DistancePicker } from "./DistancePicker";
import { PartyStepper } from "./PartyStepper";

// Order: vibe → when → budget → where → how far → who.
export const STEP_COUNT = 6;

const PARTY_QUIPS = [
  "21+ people? That's not a side quest, that's the main quest.",
  "At that size you're not questing, you're leading a raid.",
  "Party full. Even the Fellowship stopped at nine.",
];

type Props = {
  step: number;
  answers: Answers;
  onChange: (patch: Partial<Answers>) => void;
  onStep: (step: number) => void;
  onSubmit: () => void;
};

export function Wizard({ step, answers, onChange, onStep, onSubmit }: Props) {
  const advanceTimer = useRef<ReturnType<typeof setTimeout>>(undefined);
  const [timeError, setTimeError] = useState<string>();
  const [partyQuip, setPartyQuip] = useState<string>();
  const back = step > 0 ? () => onStep(step - 1) : undefined;
  const next = () => (step === STEP_COUNT - 1 ? onSubmit() : onStep(step + 1));

  function pickVibe(value: string) {
    onChange({ category: value });
    clearTimeout(advanceTimer.current);
    advanceTimer.current = setTimeout(() => onStep(1), 280);
  }

  // `key` remounts each step so its entrance animation replays.
  switch (step) {
    case 0:
      return (
        <StepFrame key={0} title="What's the vibe?" hint="Pick one. You can change it later." onNext={next} canContinue={!!answers.category}>
          <VibeOptions value={answers.category} onPick={pickVibe} />
        </StepFrame>
      );
    case 1: {
      // Checked on Continue (not during render) because it depends on the current time.
      const nextIfUpcoming = () => {
        if (new Date(answers.start).getTime() < Date.now() - 60_000) setTimeError("That leave time has already passed.");
        else next();
      };
      return (
        <StepFrame key={1} title="When are you free?" hint="When you head out, and when you need to be back." onBack={back} onNext={nextIfUpcoming} canContinue={!!answers.start && !timeError}>
          {answers.start && (
            <ClockWindow
              start={answers.start}
              end={answers.end}
              onChange={(start, end) => {
                setTimeError(undefined);
                onChange({ start, end });
              }}
              error={timeError}
            />
          )}
        </StepFrame>
      );
    }
    case 2:
      return (
        <StepFrame key={2} title="How much per person?" hint="Rough is fine. We'll flag anything that's an estimate." onBack={back} onNext={next}>
          <BigRange
            label="Budget per person"
            min={0}
            max={BUDGET_MAX}
            typedMax={BUDGET_TYPED_MAX}
            increment={5}
            value={answers.budget}
            onChange={(budget) => onChange({ budget })}
            format={formatBudget}
            prefix="$"
          />
        </StepFrame>
      );
    case 3:
      return (
        <StepFrame key={3} title="Where are you starting?" hint="Pick a neighborhood or use your current location." onBack={back} onNext={next}>
          <LocationInput value={answers.location} onChange={(location) => onChange({ location })} />
        </StepFrame>
      );
    case 4: {
      const label = answers.location.label?.trim();
      return (
        <StepFrame
          key={4}
          title="How far will you go?"
          hint={!label || label === MY_LOCATION_LABEL ? "From where you are now." : `From ${label}.`}
          onBack={back}
          onNext={next}
        >
          <DistancePicker value={answers.distance} onChange={(distance) => onChange({ distance })} location={answers.location} />
        </StepFrame>
      );
    }
    default:
      return (
        <StepFrame key={5} title="Who's coming?" hint="Including you." onBack={back} onNext={next} nextLabel="Find my side quest" footnote={partyQuip}>
          <PartyStepper
            value={answers.groupSize}
            onChange={(groupSize) => {
              if (groupSize < answers.groupSize) setPartyQuip(undefined);
              onChange({ groupSize });
            }}
            onOverflow={() =>
              setPartyQuip((prev) => PARTY_QUIPS[(PARTY_QUIPS.indexOf(prev ?? "") + 1) % PARTY_QUIPS.length])
            }
          />
        </StepFrame>
      );
  }
}
