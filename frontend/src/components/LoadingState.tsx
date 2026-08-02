import { useEffect, useState } from 'react';

const SKELETON_ROWS = [0, 1, 2];
const SLOW_MESSAGE_DELAY_MS = 3000;

export function LoadingState() {
  const [isSlow, setIsSlow] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsSlow(true), SLOW_MESSAGE_DELAY_MS);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col gap-3">
      <p role="status" aria-live="polite" className="text-sm text-ink-secondary">
        {isSlow ? 'Still working — large collections can take a few seconds.' : 'Analyzing your collection…'}
      </p>

      {/* Purely decorative — the status text above already covers the
          accessible announcement, so this is hidden from assistive tech
          rather than read out as a series of empty rows. */}
      <div aria-hidden="true" className="flex flex-col gap-3">
        {SKELETON_ROWS.map((row) => (
          <div
            key={row}
            className="flex animate-pulse gap-3 rounded border border-line-default bg-surface-raised p-3 motion-reduce:animate-none"
          >
            <div className="aspect-art w-32 shrink-0 rounded bg-surface-overlay" />
            <div className="flex flex-1 flex-col gap-2 py-1">
              <div className="h-4 w-3/4 rounded bg-surface-overlay" />
              <div className="h-3 w-1/2 rounded bg-surface-overlay" />
              <div className="h-3 w-full rounded bg-surface-overlay" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
