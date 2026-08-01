export function LoadingState() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="rounded border border-line-default bg-surface-raised p-4 text-sm text-ink-secondary"
    >
      <p>Analyzing your collection…</p>
    </div>
  );
}
