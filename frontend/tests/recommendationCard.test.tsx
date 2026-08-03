import { strict as assert } from 'node:assert';
import { test } from 'node:test';
import { renderToStaticMarkup } from 'react-dom/server';
import { RecommendationCard } from '../src/components/RecommendationCard.js';

test('links the commander image, name, and supporting cards to Scryfall', () => {
  const commanderUrl = 'https://scryfall.com/search?q=oracleid%3Acommander-id';
  const supportingCardUrl = 'https://scryfall.com/search?q=oracleid%3Asupport-id';
  const markup = renderToStaticMarkup(
    <RecommendationCard
      name="Linked Commander"
      image_url="https://cards.scryfall.io/normal/front/a/b/card.jpg"
      scryfall_url={commanderUrl}
      color_identity={['G']}
      owned={false}
      matching_themes={['graveyard']}
      theme_support={[
        {
          theme: 'graveyard',
          supporting_card_count: 1,
          example_cards: [
            {
              oracle_id: 'support-id',
              scryfall_id: 'support-print-id',
              scryfall_url: supportingCardUrl,
              image_url: 'https://cards.scryfall.io/normal/front/c/d/support.jpg',
              name: 'Eternal Witness',
              quantity: 1,
              edhrec_rank: 100,
            },
          ],
        },
      ]}
      score_breakdown={{
        theme_ratio: 0.8,
        theme_contribution: 0.6,
        color_ratio: 1,
        color_contribution: 0.2,
        popularity_score: 0.5,
        popularity_contribution: 0.025,
        final_score: 0.825,
      }}
      rank={1}
      presentation={{
        primaryTheme: 'graveyard',
        explanation: 'Graveyard stands out.',
      }}
      selectedTheme={null}
      onThemeClick={() => undefined}
    />,
  );

  assert.equal(markup.split(`href="${commanderUrl}"`).length - 1, 2);
  assert.ok(markup.includes(`href="${supportingCardUrl}"`));
  assert.match(markup, /target="_blank"/);
  assert.match(markup, /rel="noopener noreferrer"/);
});
