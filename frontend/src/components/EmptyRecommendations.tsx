import { formatThemeList } from '../content/themeLabels';

interface EmptyRecommendationsProps {
  topThemes: string[];
}

export function EmptyRecommendations({ topThemes }: EmptyRecommendationsProps) {
  const themeClause =
    topThemes.length > 0
      ? ` matched your collection's dominant themes (${formatThemeList(topThemes)}) closely enough`
      : ' had a strong enough theme match';

  return (
    <div className="rounded border border-line-default bg-surface-raised p-4 text-sm text-ink-secondary">
      <p className="font-medium text-ink-primary">No commander matched your collection closely enough.</p>
      <p className="mt-2">
        None of the eligible commanders{themeClause} to recommend. Try uploading a larger
        collection, or double-check that your CSV lists recognizable Magic card names.
      </p>
    </div>
  );
}
