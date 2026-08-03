import type { CommanderRecommendation, SupportingCard, ThemeSupport } from '../types/api.js';
import { getThemeLabel } from './themeLabels.js';

type PresentationSource = Pick<
  CommanderRecommendation,
  'matching_themes' | 'theme_support'
>;

interface EvidenceCandidate {
  card: SupportingCard;
  cardOrder: number;
}

export interface RecommendationPresentation {
  primaryTheme: string | null;
  explanation: string;
}

function incrementCount(counts: Map<string, number>, key: string): void {
  counts.set(key, (counts.get(key) ?? 0) + 1);
}

function getThemeSupport(
  recommendation: PresentationSource,
  theme: string,
): ThemeSupport | undefined {
  return recommendation.theme_support.find((support) => support.theme === theme);
}

function selectPrimaryTheme(
  recommendation: PresentationSource,
  themeFrequency: Map<string, number>,
  selectedThemeCounts: Map<string, number>,
  selectedTheme: string | null,
): string | null {
  if (selectedTheme && recommendation.matching_themes.includes(selectedTheme)) {
    return selectedTheme;
  }

  const themes = [...recommendation.matching_themes];

  themes.sort((themeA, themeB) => {
    const supportA = getThemeSupport(recommendation, themeA)?.supporting_card_count ?? 0;
    const supportB = getThemeSupport(recommendation, themeB)?.supporting_card_count ?? 0;

    return (
      supportB - supportA
      || (selectedThemeCounts.get(themeA) ?? 0) - (selectedThemeCounts.get(themeB) ?? 0)
      || (themeFrequency.get(themeA) ?? 0) - (themeFrequency.get(themeB) ?? 0)
      || recommendation.matching_themes.indexOf(themeA)
        - recommendation.matching_themes.indexOf(themeB)
    );
  });

  return themes[0] ?? null;
}

function buildExplanation(
  primaryTheme: string | null,
  support: ThemeSupport | undefined,
  card: SupportingCard | null,
): string {
  if (!primaryTheme) {
    return 'Matches your color identity, but no collection theme evidence is available.';
  }

  const themeLabel = getThemeLabel(primaryTheme);
  const supportingCardCount = support?.supporting_card_count ?? 0;

  if (card) {
    const cardWord = supportingCardCount === 1 ? 'card' : 'cards';
    return `${themeLabel} stands out: ${supportingCardCount} compatible ${cardWord} you own, including ${card.name}.`;
  }

  if (supportingCardCount > 0) {
    const cardWord = supportingCardCount === 1 ? 'card' : 'cards';
    return `${themeLabel} stands out, supported by ${supportingCardCount} compatible ${cardWord} you own.`;
  }

  return `${themeLabel} is this commander's clearest theme match.`;
}

export function buildRecommendationPresentations(
  recommendations: PresentationSource[],
  selectedTheme: string | null = null,
): RecommendationPresentation[] {
  const themeFrequency = new Map<string, number>();
  const cardFrequency = new Map<string, number>();
  const selectedThemeCounts = new Map<string, number>();
  const selectedCardIds = new Set<string>();

  for (const recommendation of recommendations) {
    recommendation.matching_themes.forEach((theme) => incrementCount(themeFrequency, theme));

    const recommendationCardIds = new Set<string>();
    for (const support of recommendation.theme_support) {
      if (!recommendation.matching_themes.includes(support.theme)) {
        continue;
      }
      support.example_cards.forEach((card) => recommendationCardIds.add(card.oracle_id));
    }
    recommendationCardIds.forEach((cardId) => incrementCount(cardFrequency, cardId));
  }

  return recommendations.map((recommendation) => {
    const primaryTheme = selectPrimaryTheme(
      recommendation,
      themeFrequency,
      selectedThemeCounts,
      selectedTheme,
    );
    const support = primaryTheme ? getThemeSupport(recommendation, primaryTheme) : undefined;
    const evidenceCandidates: EvidenceCandidate[] = (support?.example_cards ?? [])
      .map((card, cardOrder) => ({ card, cardOrder }))
      .filter((candidate) => !selectedCardIds.has(candidate.card.oracle_id));

    evidenceCandidates.sort((candidateA, candidateB) => (
      (cardFrequency.get(candidateA.card.oracle_id) ?? 0)
        - (cardFrequency.get(candidateB.card.oracle_id) ?? 0)
      || (candidateB.card.edhrec_rank ?? -1) - (candidateA.card.edhrec_rank ?? -1)
      || candidateA.cardOrder - candidateB.cardOrder
      || candidateA.card.name.localeCompare(candidateB.card.name)
    ));

    const selectedEvidence = evidenceCandidates[0];
    const card = selectedEvidence?.card ?? null;

    if (primaryTheme) {
      incrementCount(selectedThemeCounts, primaryTheme);
    }
    if (card) {
      selectedCardIds.add(card.oracle_id);
    }

    return {
      primaryTheme,
      explanation: buildExplanation(primaryTheme, support, card),
    };
  });
}
