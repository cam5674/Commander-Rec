import type { APIErrorDetail } from '../types/api';
import { CSV_FORMAT_HINT } from '../content/csvFormat';
import { UnmatchedCardsNotice } from './UnmatchedCardsNotice';

interface ErrorStateProps {
  error: APIErrorDetail;
}

export function ErrorState({ error }: ErrorStateProps) {
  const hasUnmatchedNames = error.unmatched_names.length > 0;
  const hasWarnings = error.warnings.length > 0;

  return (
    <div
      role="alert"
      className="rounded border border-line-default border-l-4 border-l-status-danger bg-surface-raised p-4"
    >
      <p className="font-medium text-ink-primary">{error.message}</p>

      {error.code === 'INVALID_CSV' && (
        <p className="mt-2 rounded border border-dashed border-line-subtle p-3 text-sm text-ink-secondary">
          {CSV_FORMAT_HINT}
        </p>
      )}

      {error.code === 'NO_RECOGNIZED_CARDS' && (hasUnmatchedNames || hasWarnings) && (
        <div className="mt-2">
          <UnmatchedCardsNotice unmatchedNames={error.unmatched_names} warnings={error.warnings} />
        </div>
      )}
    </div>
  );
}
