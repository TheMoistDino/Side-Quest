"use client";

import { useRef } from "react";
import { formatDuration, formatTime, toDateTimeLocal } from "@/lib/format";

// A 24-hour dial: midnight at the top, noon at the bottom, clockwise.
// Drag either handle to set leave / back-by, or drag the highlighted arc to move both.

const SIZE = 316; // ring plus room for the hour labels outside it
const C = SIZE / 2;
const R = 118;
const LABEL_R = R + 28;
const DAY = 1440;
const SNAP = 15;
const MIN_WINDOW = 30;
const DAYS_AHEAD = 7;

type Props = {
  start: string; // datetime-local
  end: string;
  onChange: (start: string, end: string) => void;
  error?: string;
};

type Drag = { kind: "start" | "end" } | { kind: "arc"; offset: number };

const mod = (n: number, m: number) => ((n % m) + m) % m;
const snap = (min: number) => mod(Math.round(min / SNAP) * SNAP, DAY);

function point(min: number) {
  const a = (min / DAY) * 2 * Math.PI;
  return { x: C + R * Math.sin(a), y: C - R * Math.cos(a) };
}

function startOfDay(d: Date) {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function ClockWindow({ start, end, onChange, error }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const drag = useRef<Drag | null>(null);

  const startDate = new Date(start);
  const day = startOfDay(startDate);
  const startMin = startDate.getHours() * 60 + startDate.getMinutes();
  const duration = Math.round((new Date(end).getTime() - startDate.getTime()) / 60_000);
  const endMin = mod(startMin + duration, DAY);

  function emit(nextDay: Date, nextStartMin: number, nextDuration: number) {
    const s = new Date(nextDay.getTime() + nextStartMin * 60_000);
    const e = new Date(s.getTime() + nextDuration * 60_000);
    onChange(toDateTimeLocal(s), toDateTimeLocal(e));
  }

  // Moving the start keeps the back-by time of day fixed (and vice versa).
  function setStartMin(m: number) {
    const d = mod(endMin - m, DAY);
    if (d >= MIN_WINDOW) emit(day, m, d);
  }
  function setEndMin(m: number) {
    const d = mod(m - startMin, DAY);
    if (d >= MIN_WINDOW) emit(day, startMin, d);
  }

  function pointerMinutes(e: React.PointerEvent) {
    const rect = svgRef.current!.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * SIZE - C;
    const y = ((e.clientY - rect.top) / rect.height) * SIZE - C;
    const deg = mod((Math.atan2(x, -y) * 180) / Math.PI, 360);
    return (deg / 360) * DAY;
  }

  function onPointerDown(e: React.PointerEvent, kind: Drag["kind"]) {
    e.preventDefault();
    try {
      svgRef.current?.setPointerCapture(e.pointerId);
    } catch {
      // Pointer already released; dragging still works while it stays over the dial.
    }
    drag.current = kind === "arc" ? { kind, offset: pointerMinutes(e) - startMin } : { kind };
  }

  function onPointerMove(e: React.PointerEvent) {
    const d = drag.current;
    if (!d) return;
    const m = pointerMinutes(e);
    if (d.kind === "arc") emit(day, snap(m - d.offset), duration);
    else if (d.kind === "start") setStartMin(snap(m));
    else setEndMin(snap(m));
  }

  function onKey(e: React.KeyboardEvent, which: "start" | "end") {
    const step = e.shiftKey ? 60 : SNAP;
    const delta = { ArrowRight: step, ArrowUp: step, ArrowLeft: -step, ArrowDown: -step }[e.key];
    if (!delta) return;
    e.preventDefault();
    if (which === "start") setStartMin(mod(startMin + delta, DAY));
    else setEndMin(mod(endMin + delta, DAY));
  }

  const today = startOfDay(new Date());
  const days = Array.from({ length: DAYS_AHEAD }, (_, i) => new Date(today.getTime() + i * 86_400_000));

  const p1 = point(startMin);
  const p2 = point(endMin);
  const arc = `M ${p1.x} ${p1.y} A ${R} ${R} 0 ${duration > DAY / 2 ? 1 : 0} 1 ${p2.x} ${p2.y}`;
  const crossesMidnight = startMin + duration >= DAY;

  const handle = (which: "start" | "end", p: { x: number; y: number }, min: number) => (
    <circle
      cx={p.x}
      cy={p.y}
      r={12}
      role="slider"
      tabIndex={0}
      aria-label={which === "start" ? "Leave time" : "Back-by time"}
      aria-valuemin={0}
      aria-valuemax={DAY - SNAP}
      aria-valuenow={min}
      aria-valuetext={formatTime(new Date(day.getTime() + min * 60_000).toISOString())}
      onPointerDown={(e) => onPointerDown(e, which)}
      onKeyDown={(e) => onKey(e, which)}
      className="cursor-grab fill-text outline-none focus-visible:stroke-sign focus-visible:stroke-[4] active:cursor-grabbing"
    />
  );

  return (
    <div className="flex flex-col gap-6">
      <div role="radiogroup" aria-label="Day" className="-mx-6 flex gap-1.5 overflow-x-auto px-6 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {days.map((d, i) => {
          const selected = d.getTime() === day.getTime();
          return (
            <button
              key={d.toISOString()}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => emit(d, startMin, duration)}
              className={[
                "shrink-0 rounded-full border px-3 py-1.5 text-[13px] transition",
                selected ? "border-text bg-text font-semibold text-bg" : "border-line font-medium text-muted hover:border-muted",
              ].join(" ")}
            >
              {i === 0 ? "Today" : d.toLocaleDateString([], { weekday: "short" })}
            </button>
          );
        })}
      </div>

      <div className="relative mx-auto aspect-square w-full max-w-[316px]">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${SIZE} ${SIZE}`}
          className="absolute inset-0 size-full touch-none select-none"
          onPointerMove={onPointerMove}
          onPointerUp={() => (drag.current = null)}
          onPointerCancel={() => (drag.current = null)}
        >
          <circle cx={C} cy={C} r={R} fill="none" className="stroke-line" strokeWidth={18} />
          <path
            d={arc}
            fill="none"
            className="cursor-grab stroke-sign active:cursor-grabbing"
            strokeWidth={18}
            strokeLinecap="round"
            onPointerDown={(e) => onPointerDown(e, "arc")}
          />
          {/* Hour labels sit outside the ring so long durations in the center never collide with them. */}
          {[
            ["12a", C, C - LABEL_R + 4],
            ["6a", C + LABEL_R, C + 4],
            ["12p", C, C + LABEL_R + 4],
            ["6p", C - LABEL_R, C + 4],
          ].map(([label, x, y]) => (
            <text key={label} x={x} y={y} textAnchor="middle" className="fill-muted text-[11px] font-medium" aria-hidden>
              {label}
            </text>
          ))}
          {handle("start", p1, startMin)}
          {handle("end", p2, endMin)}
        </svg>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 text-center">
          <span className="font-display text-[40px] leading-[42px] font-extrabold tracking-tight text-sign tabular-nums whitespace-nowrap">
            {formatDuration(duration, { compact: true })}
          </span>
          <span className="text-sm font-medium tabular-nums">
            {formatTime(startDate.toISOString())} → {formatTime(new Date(end).toISOString())}
          </span>
          {crossesMidnight && <span className="text-xs text-muted">ends next day</span>}
        </div>
      </div>

      <p className={`min-h-5 text-center text-sm ${error ? "text-danger" : "text-muted"}`} aria-live="polite">
        {error ?? "Drag the dots, or the yellow arc to slide both."}
      </p>
    </div>
  );
}
