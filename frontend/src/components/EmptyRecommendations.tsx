export function EmptyRecommendations() {
  return (
    <div className="rounded border border-line-default bg-surface-raised p-4 text-sm text-ink-secondary">
      <p className="font-medium text-ink-primary">No commander recommendations found.</p>
      <p className="mt-2">
        Your collection didn&apos;t have a strong enough theme match for any eligible
        commander. Try uploading a larger collection, or double-check that your CSV lists
        recognizable Magic card names.
      </p>
    </div>
  );
}
