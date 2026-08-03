import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { buildRecommendationPresentations } from '../src/content/recommendationPresentation.js';
import type { CommanderRecommendation, ThemeSupport } from '../src/types/api.js';

type PresentationSource = Pick<
  CommanderRecommendation,
  'matching_themes' | 'theme_support'
>;

function support(
  theme: string,
  supportingCardCount: number,
  cards: Array<[oracleId: string, name: string]>,
): ThemeSupport {
  return {
    theme,
    supporting_card_count: supportingCardCount,
    example_cards: cards.map(([oracleId, name], index) => ({
      oracle_id: oracleId,
      name,
      quantity: 1,
      edhrec_rank: 100 + index,
    })),
  };
}

test('selects commander-specific evidence before a repeated staple', () => {
  const recommendations: PresentationSource[] = [
    {
      matching_themes: ['artifacts'],
      theme_support: [support('artifacts', 8, [
        ['mind-stone', 'Mind Stone'],
        ['ichor-wellspring', 'Ichor Wellspring'],
      ])],
    },
    {
      matching_themes: ['artifacts'],
      theme_support: [support('artifacts', 6, [
        ['mind-stone', 'Mind Stone'],
        ['scrap-trawler', 'Scrap Trawler'],
      ])],
    },
  ];

  const presentations = buildRecommendationPresentations(recommendations);

  assert.match(presentations[0].explanation, /Ichor Wellspring/);
  assert.match(presentations[1].explanation, /Scrap Trawler/);
  assert.doesNotMatch(presentations[0].explanation, /Mind Stone/);
  assert.doesNotMatch(presentations[1].explanation, /Mind Stone/);
});

test('never repeats an example card across the visible set', () => {
  const recommendations: PresentationSource[] = [
    {
      matching_themes: ['card_draw'],
      theme_support: [support('card_draw', 5, [['mind-stone', 'Mind Stone']])],
    },
    {
      matching_themes: ['card_draw'],
      theme_support: [support('card_draw', 4, [['mind-stone', 'Mind Stone']])],
    },
  ];

  const explanations = buildRecommendationPresentations(recommendations)
    .map((presentation) => presentation.explanation)
    .join(' ');

  assert.equal(explanations.match(/Mind Stone/g)?.length, 1);
  assert.match(explanations, /supported by 4 compatible cards you own/);
});

test('rotates the key theme when recommendations have identical theme sets', () => {
  const recommendations: PresentationSource[] = [
    {
      matching_themes: ['artifacts', 'graveyard'],
      theme_support: [support('artifacts', 3, []), support('graveyard', 3, [])],
    },
    {
      matching_themes: ['artifacts', 'graveyard'],
      theme_support: [support('artifacts', 3, []), support('graveyard', 3, [])],
    },
  ];

  const presentations = buildRecommendationPresentations(recommendations);

  assert.equal(presentations[0].primaryTheme, 'artifacts');
  assert.equal(presentations[1].primaryTheme, 'graveyard');
});

test('uses the theme with the most compatible cards by default', () => {
  const recommendations: PresentationSource[] = [
    {
      matching_themes: ['artifacts', 'graveyard'],
      theme_support: [
        support('artifacts', 12, [['mind-stone', 'Mind Stone']]),
        support('graveyard', 49, [['eternal-witness', 'Eternal Witness']]),
      ],
    },
  ];

  const [presentation] = buildRecommendationPresentations(recommendations);

  assert.equal(presentation.primaryTheme, 'graveyard');
  assert.equal(
    presentation.explanation,
    'Graveyard stands out: 49 compatible cards you own, including Eternal Witness.',
  );
});

test('uses a clicked theme for the key theme and explanation', () => {
  const recommendations: PresentationSource[] = [
    {
      matching_themes: ['artifacts', 'graveyard'],
      theme_support: [
        support('artifacts', 12, [['mind-stone', 'Mind Stone']]),
        support('graveyard', 49, [['eternal-witness', 'Eternal Witness']]),
      ],
    },
  ];

  const [presentation] = buildRecommendationPresentations(recommendations, 'artifacts');

  assert.equal(presentation.primaryTheme, 'artifacts');
  assert.equal(
    presentation.explanation,
    'Artifacts stands out: 12 compatible cards you own, including Mind Stone.',
  );
});
