// Backend theme tags are snake_case identifiers (see scripts/process_scryfall.py
// THEME_RULES) — not user-facing copy. This maps the known set to readable
// labels, with a generic fallback for any theme added later without a
// matching frontend update.
const THEME_LABELS: Record<string, string> = {
  reanimator: 'Reanimator',
  graveyard: 'Graveyard',
  sacrifice: 'Sacrifice',
  tokens: 'Tokens',
  artifacts: 'Artifacts',
  lifegain: 'Lifegain',
  plus_one_counters: '+1/+1 Counters',
  spellslinger: 'Spellslinger',
  card_draw: 'Card Draw',
  lands: 'Lands',
  aristocrats: 'Aristocrats',
  wheels: 'Wheels',
};

function titleCaseFallback(theme: string): string {
  return theme
    .split('_')
    .map((word) => (word ? word.charAt(0).toUpperCase() + word.slice(1) : word))
    .join(' ');
}

export function getThemeLabel(theme: string): string {
  return THEME_LABELS[theme] ?? titleCaseFallback(theme);
}

export function formatThemeList(themes: string[]): string {
  const labels = themes.map(getThemeLabel);

  if (labels.length === 0) {
    return '';
  }
  if (labels.length === 1) {
    return labels[0];
  }
  if (labels.length === 2) {
    return `${labels[0]} and ${labels[1]}`;
  }
  return `${labels.slice(0, -1).join(', ')}, and ${labels[labels.length - 1]}`;
}

export function buildExplanation(matchingThemes: string[]): string {
  if (matchingThemes.length === 0) {
    return 'Matches your color identity.';
  }
  const themeWord = matchingThemes.length === 1 ? 'theme' : 'themes';
  return `Matches your ${formatThemeList(matchingThemes)} ${themeWord}.`;
}
