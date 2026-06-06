import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '@/lib/useReducedMotion';

interface CounterProps {
  /** Target value to settle on. */
  value: number;
  /** Render the (interpolated) number as a string. Defaults to a rounded int. */
  format?: (n: number) => string;
  /** Roll duration in ms. */
  duration?: number;
  className?: string;
}

/**
 * A readout that rolls up from zero to `value` on mount — the instrument-grade
 * "data just landed" feedback for KPI figures. Animates a single state value
 * via requestAnimationFrame (not per-frame React churn across a tree), and
 * snaps straight to the final value when the user prefers reduced motion.
 */
export function Counter({ value, format = (n) => String(Math.round(n)), duration = 900, className }: CounterProps) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(0);
  const frame = useRef<number | null>(null);

  useEffect(() => {
    // Reduced motion: skip the roll entirely. The final value is shown directly
    // at render time, so there is nothing to animate or set here.
    if (reduce) return;

    const start = performance.now();
    const from = 0;
    // easeOutExpo — fast to settle, like a gauge needle finding its mark.
    const ease = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1);
      setDisplay(from + (value - from) * ease(t));
      if (t < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);

    return () => {
      if (frame.current != null) cancelAnimationFrame(frame.current);
    };
  }, [value, duration, reduce]);

  return (
    <span className={className} data-money>
      {format(reduce ? value : display)}
    </span>
  );
}
