import { useEffect } from 'react';
import Lenis from '@studio-freight/lenis';
import { gsap, ScrollTrigger } from './motion';

/**
 * Global Lenis smooth-scroll, driven by GSAP's ticker so it stays in lockstep
 * with every ScrollTrigger. Only runs when `enabled` is true — the caller gates
 * it on a desktop pointer, a non-mobile viewport, and no reduced-motion
 * preference, so touch devices and reduced-motion users get native scroll.
 *
 * Damping (lerp) 0.1, duration 1.2. Cleans up the ticker callback, the
 * ScrollTrigger bridge, and the Lenis instance on teardown to avoid leaks.
 */
export function useSmoothScroll(enabled: boolean) {
  useEffect(() => {
    if (!enabled) return;

    const lenis = new Lenis({ lerp: 0.1, duration: 1.2 });

    // Keep ScrollTrigger's cached scroll position synced to Lenis.
    lenis.on('scroll', ScrollTrigger.update);

    const onTick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(onTick);
    // Lenis owns the rAF cadence; disable gsap's lag smoothing so they agree.
    gsap.ticker.lagSmoothing(0);

    return () => {
      gsap.ticker.remove(onTick);
      lenis.off('scroll', ScrollTrigger.update);
      lenis.destroy();
      gsap.ticker.lagSmoothing(500, 33);
    };
  }, [enabled]);
}
