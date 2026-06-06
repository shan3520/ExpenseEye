import { useEffect, useRef, useState } from 'react';

/**
 * Reveals an element the first time it scrolls into view. Returns a ref to
 * attach and a flag that flips to `true` on first intersection (and stays true —
 * tiles don't re-hide once seen). Falls back to immediately-visible when
 * IntersectionObserver is unavailable, so content never gets stuck hidden.
 */
export function useInView<T extends HTMLElement>(rootMargin = '0px 0px -12% 0px') {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(() => typeof IntersectionObserver === 'undefined');

  useEffect(() => {
    if (inView) return;
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setInView(true);
          io.disconnect();
        }
      },
      { rootMargin, threshold: 0.08 }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [inView, rootMargin]);

  return { ref, inView };
}
