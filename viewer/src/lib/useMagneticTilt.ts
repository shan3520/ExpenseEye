import { useEffect, useRef } from 'react';
import { useMediaQuery } from './useMediaQuery';
import { useReducedMotion } from './useReducedMotion';

/**
 * Subtle cursor-following 3D tilt for a card. Returns a ref to attach to the
 * wrapper (which must carry `perspective`); the element marked
 * `[data-tilt-target]` inside it receives the rotateX/rotateY. Movement writes
 * transform directly (rAF-batched, transform-only) for responsiveness; release
 * eases back over 400ms. Disabled on touch (`pointer: coarse`) and under
 * reduced motion, where no listeners are attached at all.
 *
 * @param maxDeg maximum tilt on each axis, in degrees (default 3).
 */
export function useMagneticTilt<T extends HTMLElement>(maxDeg = 3) {
  const wrapRef = useRef<T | null>(null);
  const coarse = useMediaQuery('(pointer: coarse)');
  const reduce = useReducedMotion();

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap || coarse || reduce) return;

    const target = (wrap.querySelector('[data-tilt-target]') as HTMLElement | null) ?? wrap;
    let raf = 0;

    const onMove = (e: MouseEvent) => {
      const r = wrap.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width - 0.5; // -0.5 .. 0.5
      const py = (e.clientY - r.top) / r.height - 0.5;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        target.style.transition = 'transform 0ms';
        target.style.willChange = 'transform';
        target.style.transform =
          `rotateX(${(-py * 2 * maxDeg).toFixed(2)}deg) rotateY(${(px * 2 * maxDeg).toFixed(2)}deg)`;
      });
    };

    const onLeave = () => {
      cancelAnimationFrame(raf);
      target.style.transition = 'transform 400ms ease-out';
      target.style.transform = 'rotateX(0deg) rotateY(0deg)';
      const clear = () => {
        target.style.willChange = '';
        target.removeEventListener('transitionend', clear);
      };
      target.addEventListener('transitionend', clear);
    };

    wrap.addEventListener('mousemove', onMove);
    wrap.addEventListener('mouseleave', onLeave);
    return () => {
      wrap.removeEventListener('mousemove', onMove);
      wrap.removeEventListener('mouseleave', onLeave);
      cancelAnimationFrame(raf);
    };
  }, [coarse, reduce, maxDeg]);

  return wrapRef;
}
