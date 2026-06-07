import { useEffect, useState } from 'react';

/**
 * Reactively tracks a CSS media query. SSR-safe (defaults to no-match before
 * mount). Used to gate motion by device capability — `(pointer: fine)`,
 * `(pointer: coarse)`, viewport width — so touch devices keep native behaviour.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(query).matches
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mq = window.matchMedia(query);
    const onChange = () => setMatches(mq.matches);
    onChange();
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [query]);

  return matches;
}
