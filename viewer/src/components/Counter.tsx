import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '@/lib/useReducedMotion';
import { gsap, STANDARD_EASE } from '@/lib/motion';

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
 * A readout that counts up from zero to `value` the first time it scrolls into
 * view (IntersectionObserver, not a scroll listener). The tween runs on a plain
 * proxy object via gsap.to, formatting each frame through `format` in onUpdate,
 * so currency grouping stays correct mid-roll. Fires once. Under reduced motion
 * the final value renders immediately with no tween.
 */
export function Counter({ value, format = (n) => String(Math.round(n)), duration = 1200, className }: CounterProps) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(reduce ? value : 0);
  const ref = useRef<HTMLSpanElement>(null);
  const hasRun = useRef(false);

  useEffect(() => {
    // Reduced motion: the final value is rendered directly (see JSX), so there's
    // nothing to tween or set here.
    if (reduce) return;
    const el = ref.current;
    if (!el || hasRun.current) return;

    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || hasRun.current) return;
        hasRun.current = true;
        io.disconnect();
        const proxy = { n: 0 };
        gsap.to(proxy, {
          n: value,
          duration: duration / 1000,
          ease: STANDARD_EASE,
          onUpdate: () => setDisplay(proxy.n),
        });
      },
      { threshold: 0.1 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [value, duration, reduce]);

  return (
    <span ref={ref} className={className} data-money>
      {format(reduce ? value : display)}
    </span>
  );
}
