import type { APIErrorDetail } from '../types/api';
import { CSV_FORMAT_HINT } from '../content/csvFormat';

interface ErrorStateProps {
  error: APIErrorDetail;
}

export function ErrorState({ error }: ErrorStateProps) {
  const hasUnmatchedNames = error.unmatched_names.length > 0;
  const hasWarnings = error.warnings.length > 0;

  return (
    <div className="error-state" role="alert">
      <p className="error-message">{error.message}</p>

      {error.code === 'INVALID_CSV' && (
        <p className="error-callout">{CSV_FORMAT_HINT}</p>
      )}

      {error.code === 'NO_RECOGNIZED_CARDS' && (hasUnmatchedNames || hasWarnings) && (
        <div className="no-recognized-cards-detail">
          {hasUnmatchedNames && (
            <>
              <p>These card names weren&apos;t recognized:</p>
              <ul>
                {error.unmatched_names.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </>
          )}

          {hasWarnings && (
            <>
              <p>Some rows had issues:</p>
              <ul>
                {error.warnings.map((warning) => (
                  <li key={`${warning.row}-${warning.code}`}>
                    Row {warning.row}: {warning.message}
                    {warning.value ? ` ("${warning.value}")` : ''}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
