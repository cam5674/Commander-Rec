import type { ThemeSupport } from '../types/api';

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

interface SupportingCardCandidate {
  oracleId: string;
  name: string;
  themes: Set<string>;
  narrowestThemeSize: number;
  edhrecRank: number | null;
}

function selectSupportingCardNames(
  matchingThemes: string[],
  themeSupport: ThemeSupport[],
  limit: number,
): string[] {
  const matchingThemeSet = new Set(matchingThemes);
  const candidatesById = new Map<string, SupportingCardCandidate>();

  for (const support of themeSupport) {
    if (!matchingThemeSet.has(support.theme) || support.supporting_card_count === 0) {
      continue;
    }

    for (const card of support.example_cards) {
      const existingCandidate = candidatesById.get(card.oracle_id);
      if (existingCandidate) {
        existingCandidate.themes.add(support.theme);
        existingCandidate.narrowestThemeSize = Math.min(
          existingCandidate.narrowestThemeSize,
          support.supporting_card_count,
        );
        continue;
      }

      candidatesById.set(card.oracle_id, {
        oracleId: card.oracle_id,
        name: card.name,
        themes: new Set([support.theme]),
        narrowestThemeSize: support.supporting_card_count,
        edhrecRank: card.edhrec_rank,
      });
    }
  }

  const remainingCandidates = Array.from(candidatesById.values());
  const coveredThemes = new Set<string>();
  const selectedNames: string[] = [];

  while (selectedNames.length < limit && remainingCandidates.length > 0) {
    remainingCandidates.sort((candidateA, candidateB) => {
      const newThemesA = Array.from(candidateA.themes).filter(
        (theme) => !coveredThemes.has(theme),
      ).length;
      const newThemesB = Array.from(candidateB.themes).filter(
        (theme) => !coveredThemes.has(theme),
      ).length;

      return (
        newThemesB - newThemesA
        || candidateB.themes.size - candidateA.themes.size
        || candidateA.narrowestThemeSize - candidateB.narrowestThemeSize
        || (candidateB.edhrecRank ?? -1) - (candidateA.edhrecRank ?? -1)
        || candidateA.name.localeCompare(candidateB.name)
        || candidateA.oracleId.localeCompare(candidateB.oracleId)
      );
    });

    const selectedCandidate = remainingCandidates.shift();
    if (!selectedCandidate) {
      break;
    }

    selectedNames.push(selectedCandidate.name);
    selectedCandidate.themes.forEach((theme) => coveredThemes.add(theme));
  }

  return selectedNames;
}

export function buildExplanation(
  matchingThemes: string[],
  themeSupport: ThemeSupport[],
): string {
  if (matchingThemes.length === 0) {
    return 'Matches your color identity.';
  }

  const themeWord = matchingThemes.length === 1 ? 'theme' : 'themes';
  const supportingCardNames = selectSupportingCardNames(
    matchingThemes,
    themeSupport,
    2,
  );

  const themeMatch = `Matches your ${formatThemeList(matchingThemes)} ${themeWord}.`;
  if (supportingCardNames.length === 0) {
    return themeMatch;
  }

  return `${themeMatch.slice(0, -1)}, supported by ${formatReadableList(supportingCardNames)}.`;
}
