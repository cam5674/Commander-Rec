import { useId, useState } from 'react';
import { ColorIdentityStrip } from './ColorIdentityStrip';
import { ZoomableCardImage } from './ZoomableCardImage';
import { buildExplanation, getThemeLabel } from '../content/themeLabels';
import type { CommanderRecommendation } from '../types/api';

export type RecommendationCardProps = Pick<
  CommanderRecommendation,
  | 'name'
  | 'image_url'
  | 'color_identity'
  | 'owned'
  | 'matching_themes'
  | 'theme_support'
  | 'score_breakdown'
>;

export function RecommendationCard({
  name,
  image_url,
  color_identity,
  owned,
  matching_themes,
  theme_support,
  score_breakdown,
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const detailsId = useId();
  const supportingThemes = theme_support.filter((support) => support.supporting_card_count > 0);

  return (
    <div className="rounded border border-line-default bg-surface-raised p-3">
      <div className="flex items-start gap-3">
        <ZoomableCardImage imageUrl={image_url} name={name} />

        {/* Collapsed-state content: name/badge/tags/explanation are the
            secondary tier under the image, per the hierarchy pass — but
            still clearly above the expanded "drilled-in" detail below. */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-baseline gap-2">
            <p className="text-base font-semibold text-ink-primary">{name}</p>
            {owned && <span className="text-xs font-medium text-ink-secondary">✓ Owned</span>}
          </div>

          {matching_themes.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {matching_themes.map((theme) => (
                <span
                  key={theme}
                  className="rounded bg-surface-overlay px-1.5 py-0.5 text-xs text-ink-secondary"
                >
                  {getThemeLabel(theme)}
                </span>
              ))}
            </div>
          )}

          <p className="text-sm text-ink-secondary">{buildExplanation(matching_themes)}</p>

          <button
            type="button"
            onClick={() => setIsExpanded((current) => !current)}
            aria-expanded={isExpanded}
            aria-controls={detailsId}
            className="mt-1 flex items-center gap-1 self-start text-xs font-medium text-brand-action"
          >
            {isExpanded ? 'Hide details' : 'Show details'}
            <span aria-hidden="true">{isExpanded ? '▴' : '▾'}</span>
          </button>
        </div>
      </div>

      {/* Expanded-state content: drilled-in detail, visually de-emphasized
          (text-xs, muted ink) relative to the collapsed content above. */}
      {isExpanded && (
        <div
          id={detailsId}
          className="mt-3 flex flex-col gap-3 border-t border-dashed border-line-subtle pt-3 text-xs text-ink-muted"
        >
          <div>
            <p className="mb-1 font-medium text-ink-secondary">Color identity</p>
            <div className="w-32">
              <ColorIdentityStrip colorIdentity={color_identity} />
            </div>
          </div>

          <div>
            <p className="font-medium text-ink-secondary">Score breakdown</p>
            <p>Theme match: {Math.round(score_breakdown.theme_ratio * 100)}%</p>
            <p>Color fit: {Math.round(score_breakdown.color_ratio * 100)}%</p>
            <p>Popularity: {Math.round(score_breakdown.popularity_score * 100)}%</p>
            <p>Overall: {Math.round(score_breakdown.final_score * 100)}%</p>
          </div>

          {supportingThemes.length > 0 && (
            <div>
              <p className="font-medium text-ink-secondary">Supporting cards you own</p>
              {supportingThemes.map((support) => (
                <p key={support.theme}>
                  {getThemeLabel(support.theme)} ({support.supporting_card_count}):{' '}
                  {support.example_cards.map((card) => card.name).join(', ')}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
