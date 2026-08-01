import type { CSVWarning } from '../types/api';

interface UnmatchedCardsNoticeProps {
  unmatchedNames: string[];
  warnings: CSVWarning[];
}

export function UnmatchedCardsNotice({ unmatchedNames, warnings }: UnmatchedCardsNoticeProps) {
  const hasUnmatchedNames = unmatchedNames.length > 0;
  const hasWarnings = warnings.length > 0;

  return (
    <div className="rounded border border-dashed border-line-subtle p-3 text-sm text-ink-secondary">
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
  );
}
