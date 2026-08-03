import type { RecommendationData } from '../../components/RecommendationCard';
import type { SupportingCard } from '../../types/api';

function sampleScryfallUrl(identifier: string): string {
  return `https://scryfall.com/search?q=${encodeURIComponent(`oracleid:${identifier}`)}`;
}

function sampleSupportingCard(
  oracleId: string,
  name: string,
  edhrecRank: number,
): SupportingCard {
  return {
    oracle_id: oracleId,
    scryfall_id: null,
    scryfall_url: sampleScryfallUrl(oracleId),
    image_url: null,
    name,
    quantity: 1,
    edhrec_rank: edhrecRank,
  };
}

// Real cards/art from data/processed/cards_by_id.json, one per color identity,
// so contrast and legibility can be checked against actual card art rather
// than placeholder swatches. matching_themes/theme_support/score_breakdown
// are illustrative fake values (not real API output) — enough to exercise
// the badge/tags/explanation/expand-collapse UI in isolation. Interactive
// props (selectedTheme/onThemeClick) are supplied by StyleGuidePage, not
// baked into this static data.
export const SAMPLE_COMMANDERS: RecommendationData[] = [
  {
    name: 'Loran of the Third Path',
    color_identity: ['W'],
    image_url:
      'https://cards.scryfall.io/normal/front/9/e/9e83a0ef-4fea-45ba-86c0-130d6687f7fe.jpg?1783913028',
    scryfall_url: sampleScryfallUrl('loran-third-path'),
    owned: true,
    matching_themes: ['artifacts'],
    theme_support: [
      {
        theme: 'artifacts',
        supporting_card_count: 6,
        example_cards: [
          sampleSupportingCard('sample-1a', 'Sol Ring', 1),
          sampleSupportingCard('sample-1b', 'Arcane Signet', 12),
        ],
      },
    ],
    score_breakdown: {
      theme_ratio: 0.82,
      theme_contribution: 0.615,
      color_ratio: 0.9,
      color_contribution: 0.18,
      popularity_score: 0.65,
      popularity_contribution: 0.0325,
      final_score: 0.8275,
    },
  },
  {
    name: 'Emry, Lurker of the Loch',
    color_identity: ['U'],
    image_url:
      'https://cards.scryfall.io/normal/front/c/9/c977d89a-bfd1-4e98-9d95-3e41c53dd188.jpg?1783906044',
    scryfall_url: sampleScryfallUrl('emry-lurker'),
    owned: false,
    matching_themes: ['artifacts', 'spellslinger'],
    theme_support: [
      {
        theme: 'artifacts',
        supporting_card_count: 4,
        example_cards: [sampleSupportingCard('sample-2a', 'Mind Stone', 340)],
      },
      { theme: 'spellslinger', supporting_card_count: 0, example_cards: [] },
    ],
    score_breakdown: {
      theme_ratio: 0.7,
      theme_contribution: 0.525,
      color_ratio: 0.85,
      color_contribution: 0.17,
      popularity_score: 0.55,
      popularity_contribution: 0.0275,
      final_score: 0.7225,
    },
  },
  {
    name: 'Syr Konrad, the Grim',
    color_identity: ['B'],
    image_url:
      'https://cards.scryfall.io/normal/front/4/4/443a4eac-f972-4027-aed4-552d4edc2ce1.jpg?1783909613',
    scryfall_url: sampleScryfallUrl('syr-konrad'),
    owned: true,
    matching_themes: ['graveyard', 'reanimator'],
    theme_support: [
      {
        theme: 'graveyard',
        supporting_card_count: 8,
        example_cards: [
          sampleSupportingCard('sample-3a', 'Entomb', 210),
          sampleSupportingCard('sample-3b', 'Reanimate', 95),
        ],
      },
      {
        theme: 'reanimator',
        supporting_card_count: 3,
        example_cards: [sampleSupportingCard('sample-3c', 'Animate Dead', 180)],
      },
    ],
    score_breakdown: {
      theme_ratio: 0.9,
      theme_contribution: 0.675,
      color_ratio: 0.8,
      color_contribution: 0.16,
      popularity_score: 0.7,
      popularity_contribution: 0.035,
      final_score: 0.87,
    },
  },
  {
    name: 'Ragavan, Nimble Pilferer',
    color_identity: ['R'],
    image_url:
      'https://cards.scryfall.io/normal/front/a/9/a9738cda-adb1-47fb-9f4c-ecd930228c4d.jpg?1783926839',
    scryfall_url: sampleScryfallUrl('ragavan'),
    owned: false,
    matching_themes: ['card_draw'],
    theme_support: [{ theme: 'card_draw', supporting_card_count: 0, example_cards: [] }],
    score_breakdown: {
      theme_ratio: 0.5,
      theme_contribution: 0.375,
      color_ratio: 0.95,
      color_contribution: 0.19,
      popularity_score: 0.98,
      popularity_contribution: 0.049,
      final_score: 0.614,
    },
  },
  {
    name: 'Azusa, Lost but Seeking',
    color_identity: ['G'],
    image_url:
      'https://cards.scryfall.io/normal/front/2/f/2fe97fbe-a6d6-4e96-8c26-f81bcdf579a1.jpg?1783915637',
    scryfall_url: sampleScryfallUrl('azusa'),
    owned: true,
    matching_themes: ['lands'],
    theme_support: [
      {
        theme: 'lands',
        supporting_card_count: 10,
        example_cards: [
          sampleSupportingCard('sample-5a', 'Cultivate', 60),
          sampleSupportingCard('sample-5b', 'Rampant Growth', 140),
        ],
      },
    ],
    score_breakdown: {
      theme_ratio: 0.88,
      theme_contribution: 0.66,
      color_ratio: 0.75,
      color_contribution: 0.15,
      popularity_score: 0.6,
      popularity_contribution: 0.03,
      final_score: 0.84,
    },
  },
  {
    name: 'Muldrotha, the Gravetide',
    color_identity: ['B', 'G', 'U'],
    image_url:
      'https://cards.scryfall.io/normal/front/7/0/705b4d97-2f50-47f7-9053-d748f4337553.jpg?1783904538',
    scryfall_url: sampleScryfallUrl('muldrotha'),
    owned: false,
    matching_themes: ['graveyard', 'sacrifice'],
    theme_support: [
      {
        theme: 'graveyard',
        supporting_card_count: 5,
        example_cards: [sampleSupportingCard('sample-6a', 'Eternal Witness', 220)],
      },
      { theme: 'sacrifice', supporting_card_count: 0, example_cards: [] },
    ],
    score_breakdown: {
      theme_ratio: 0.77,
      theme_contribution: 0.5775,
      color_ratio: 0.6,
      color_contribution: 0.12,
      popularity_score: 0.4,
      popularity_contribution: 0.02,
      final_score: 0.7175,
    },
  },
  {
    name: 'Kozilek, Butcher of Truth',
    color_identity: [],
    image_url:
      'https://cards.scryfall.io/normal/front/d/2/d27cf7b7-7982-46bd-a559-7789c0e74bae.jpg?1783921940',
    scryfall_url: sampleScryfallUrl('kozilek'),
    owned: false,
    matching_themes: ['card_draw'],
    theme_support: [
      {
        theme: 'card_draw',
        supporting_card_count: 2,
        example_cards: [sampleSupportingCard('sample-7a', 'Skullclamp', 40)],
      },
    ],
    score_breakdown: {
      theme_ratio: 0.6,
      theme_contribution: 0.45,
      color_ratio: 1.0,
      color_contribution: 0.2,
      popularity_score: 0.35,
      popularity_contribution: 0.0175,
      final_score: 0.6675,
    },
  },
];
