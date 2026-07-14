'use client';

import { useEffect, useState } from 'react';

export const compactOrTouchInputQuery = '(max-width: 767px), (hover: none) and (pointer: coarse)';

export function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;

    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);

    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [query]);

  return matches;
}

export function useCompactOrTouchInput() {
  return useMediaQuery(compactOrTouchInputQuery);
}
