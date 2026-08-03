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

  return formatReadableList(labels);
}

function formatReadableList(items: string[]): string {
  if (items.length === 0) {
    return '';
  }
  if (items.length === 1) {
    return items[0];
  }
  if (items.length === 2) {
    return `${items[0]} and ${items[1]}`;
  }
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
}
