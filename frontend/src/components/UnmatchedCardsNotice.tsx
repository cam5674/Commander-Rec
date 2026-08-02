import { useId, useState } from 'react';
import type { CSVWarning } from '../types/api';

interface UnmatchedCardsNoticeProps {
  unmatchedNames: string[];
  warnings: CSVWarning[];
  defaultExpanded?: boolean;
  emphasized?: boolean;
}

export function UnmatchedCardsNotice({
  unmatchedNames,
  warnings,
  defaultExpanded = false,
  emphasized = false,
}: UnmatchedCardsNoticeProps) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const detailsId = useId();
  const hasUnmatchedNames = unmatchedNames.length > 0;
  const hasWarnings = warnings.length > 0;
  const issueCount = unmatchedNames.length + warnings.length;

  return (
    <div
      className={`rounded border p-3 text-sm text-ink-secondary ${
        emphasized
          ? 'border-line-default bg-surface-raised'
          : 'border-dashed border-line-subtle'
      }`}
    >
      <button
        type="button"
        onClick={() => setIsExpanded((current) => !current)}
        aria-expanded={isExpanded}
        aria-controls={detailsId}
        className="flex min-h-10 w-full items-center justify-between gap-3 text-left"
      >
        <span className="font-medium text-ink-primary">
          Collection issues ({issueCount})
        </span>
        <span aria-hidden="true">{isExpanded ? '▴' : '▾'}</span>
      </button>

      {isExpanded && (
        <div id={detailsId} className="mt-2 border-t border-line-subtle pt-2">
          {hasUnmatchedNames && (
            <>
              <p>These card names weren&apos;t recognized:</p>
              <ul className="list-disc pl-5">
                {unmatchedNames.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            </>
          )}

          {hasWarnings && (
            <>
              <p className={hasUnmatchedNames ? 'mt-2' : undefined}>Some rows had issues:</p>
              <ul className="list-disc pl-5">
                {warnings.map((warning) => (
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
