import { useId, useState } from 'react';
import { ZoomableCardImage } from './ZoomableCardImage';
import { CardHoverPreview } from './CardHoverPreview';
import { getThemeLabel } from '../content/themeLabels';
import type { RecommendationPresentation } from '../content/recommendationPresentation';
import type { CommanderRecommendation } from '../types/api';

export type RecommendationData = Pick<
  CommanderRecommendation,
  | 'name'
  | 'image_url'
  | 'scryfall_url'
  | 'color_identity'
  | 'owned'
  | 'matching_themes'
  | 'theme_support'
  | 'score_breakdown'
>;

export type RecommendationCardProps = RecommendationData & {
  rank: number;
  presentation: RecommendationPresentation;
  selectedTheme: string | null;
  onThemeClick: (theme: string) => void;
};

function ScoreBar({ label, ratio }: { label: string; ratio: number }) {
  const percent = Math.round(ratio * 100);

  return (
    <div className="flex items-center gap-2">
      <span className="w-20 shrink-0">{label}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-overlay">
        <div className="h-full rounded-full bg-brand-action" style={{ width: `${percent}%` }} />
      </div>
      <span className="w-8 shrink-0 text-right">{percent}%</span>
    </div>
  );
}

export function RecommendationCard({
  name,
  image_url,
  scryfall_url,
  color_identity,
  owned,
  matching_themes,
  theme_support,
  score_breakdown,
  rank,
  presentation,
  selectedTheme,
  onThemeClick,
}: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const detailsId = useId();
  const supportingThemes = theme_support.filter((support) => support.supporting_card_count > 0);
  const orderedThemes = presentation.primaryTheme
    ? [
        presentation.primaryTheme,
        ...matching_themes.filter((theme) => theme !== presentation.primaryTheme),
      ]
    : matching_themes;

  return (
    <div className="h-full rounded border border-line-default bg-surface-raised p-3 transition-colors hover:bg-surface-overlay motion-reduce:transition-none">
      <div className="flex items-start gap-3">
        {/* Rank is anchored to the image corner rather than sharing the
            name's flex-wrap flow — as a text-flow sibling of the name it
            would get pushed onto its own line whenever the name wraps to
            two lines, so its position depended on name length. */}
        <div className="relative shrink-0">
          <ZoomableCardImage
            imageUrl={image_url}
            scryfallUrl={scryfall_url}
            name={name}
            colorIdentity={color_identity}
          />
          <span
            className="absolute left-1 top-1 rounded bg-surface-base/80 px-1.5 py-0.5 text-xs font-semibold text-ink-primary"
            aria-label={`Rank ${rank}`}
          >
            #{rank}
          </span>
        </div>

        {/* Collapsed-state content: name/badge/tags/explanation are the
            secondary tier under the image, per the hierarchy pass — but
            still clearly above the expanded "drilled-in" detail below. */}
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <div className="flex flex-wrap items-baseline gap-2">
            <a
              href={scryfall_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-base font-semibold text-ink-primary underline decoration-line-default underline-offset-2 hover:text-brand-action"
            >
              {name}
              <span className="sr-only"> (opens on Scryfall in a new tab)</span>
            </a>
            {owned && <span className="text-xs font-medium text-ink-secondary">✓ Owned</span>}
          </div>

          {matching_themes.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {orderedThemes.map((theme, index) => (
                <button
                  key={theme}
                  type="button"
                  onClick={() => onThemeClick(theme)}
                  aria-pressed={theme === selectedTheme}
                  className={`min-h-8 rounded px-2 py-1 text-xs transition-colors ${
                    theme === selectedTheme
                      ? 'bg-brand-action text-ink-on-mana'
                      : index === 0 && theme === presentation.primaryTheme
                        ? 'border border-brand-action bg-surface-overlay text-ink-primary hover:bg-line-default'
                        : 'bg-surface-overlay text-ink-secondary hover:bg-line-default'
                  }`}
                  aria-label={
                    index === 0 && theme === presentation.primaryTheme
                      ? `Key theme: ${getThemeLabel(theme)}`
                      : undefined
                  }
                >
                  {index === 0 && theme === presentation.primaryTheme ? 'Key: ' : ''}
                  {getThemeLabel(theme)}
                </button>
              ))}
            </div>
          )}

          <p className="text-sm text-ink-secondary">
            {presentation.explanation}
          </p>

          <p className="text-xs text-ink-muted">
            {Math.round(score_breakdown.final_score * 100)}% overall fit
            {' · '}{Math.round(score_breakdown.theme_ratio * 100)}% theme
            {' · '}{Math.round(score_breakdown.color_ratio * 100)}% color
          </p>

          <button
            type="button"
            onClick={() => setIsExpanded((current) => !current)}
            aria-expanded={isExpanded}
            aria-controls={detailsId}
            className="mt-1 flex min-h-10 items-center gap-1 self-start py-2 text-xs font-medium text-brand-action"
          >
            {isExpanded ? 'Hide details' : 'Show details'}
            <span aria-hidden="true">{isExpanded ? '▴' : '▾'}</span>
          </button>
        </div>
      </div>

      {/* Always mounted (not conditionally rendered) so the grid-rows
          0fr->1fr transition below has something to animate — a
          conditionally-rendered element has no "before" state to
          transition from on mount. aria-hidden keeps it out of the
          accessibility tree while collapsed regardless. */}
      <div
        id={detailsId}
        aria-hidden={!isExpanded}
        className={`grid transition-[grid-template-rows] duration-200 ease-out motion-reduce:transition-none ${
          isExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        }`}
      >
        <div className="overflow-hidden">
          {/* Expanded-state content: drilled-in detail, visually
              de-emphasized (text-xs, muted ink) relative to the collapsed
              content above. */}
          <div className="mt-3 flex flex-col gap-3 border-t border-dashed border-line-subtle pt-3 text-xs text-ink-muted">
            <div className="flex flex-col gap-1">
              <p className="font-medium text-ink-secondary">Score breakdown</p>
              <ScoreBar label="Theme match" ratio={score_breakdown.theme_ratio} />
              <ScoreBar label="Color fit" ratio={score_breakdown.color_ratio} />
              <ScoreBar label="Popularity" ratio={score_breakdown.popularity_score} />
              <ScoreBar label="Overall" ratio={score_breakdown.final_score} />
            </div>

            {supportingThemes.length > 0 && (
              <div className="flex flex-col gap-2">
                <p className="font-medium text-ink-secondary">Supporting cards you own</p>
                {supportingThemes.map((support) => (
                  <div key={support.theme} className="flex flex-col gap-1">
                    <span>{getThemeLabel(support.theme)} ({support.supporting_card_count})</span>
                    <div className="flex flex-wrap gap-1">
                      {support.example_cards.map((card) => (
                        <CardHoverPreview key={card.oracle_id} imageUrl={card.image_url} name={card.name}>
                          <a
                            href={card.scryfall_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="rounded bg-surface-overlay px-2 py-1 text-brand-action underline underline-offset-2 hover:bg-line-default"
                          >
                            {card.name}
                            <span className="sr-only"> (opens on Scryfall in a new tab)</span>
                          </a>
                        </CardHoverPreview>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
