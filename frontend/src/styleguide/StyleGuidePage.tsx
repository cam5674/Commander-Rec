import { useState } from 'react';
import { ColorSwatches } from './components/ColorSwatches';
import { TypeScaleSample } from './components/TypeScaleSample';
import { SpacingSample } from './components/SpacingSample';
import { InteractionStates } from './components/InteractionStates';
import { RecommendationCard } from '../components/RecommendationCard';
import { SAMPLE_COMMANDERS } from './data/sampleCommanders';

export function StyleGuidePage() {
  // Real local state, not a no-op — lets the click-to-filter theme chips
  // be exercised here too, matching the actual app's behavior.
  const [themeFilter, setThemeFilter] = useState<string | null>(null);

  const handleThemeClick = (theme: string) => {
    setThemeFilter((current) => (current === theme ? null : theme));
  };

  return (
    <div className="min-h-screen bg-surface-base p-8 font-sans text-ink-primary">
      <h1 className="font-display text-4xl">MTG Commander Recommender</h1>
      <p className="mt-2 text-ink-secondary">Design token reference — dev-only, not part of the shipped app.</p>

      <section className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Colors</h2>
        <ColorSwatches />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Type scale</h2>
        <TypeScaleSample />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Spacing scale</h2>
        <SpacingSample />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Interactive states</h2>
        <InteractionStates />
      </section>

      <section className="mt-10">
        <h2 className="mb-4 text-2xl font-semibold">Sample commanders</h2>
        <p className="mb-4 text-sm text-ink-secondary">
          Rendered with the real RecommendationCard component, not a lookalike demo. The
          matching_themes/theme_support/score_breakdown values here are illustrative sample
          data, not real API output — but the theme-chip filtering below is real.
        </p>
        <div className="flex max-w-2xl flex-col gap-3">
          {SAMPLE_COMMANDERS.filter(
            (commander) => !themeFilter || commander.matching_themes.includes(themeFilter),
          ).map((commander) => (
            <RecommendationCard
              key={commander.name}
              {...commander}
              rank={SAMPLE_COMMANDERS.indexOf(commander) + 1}
              selectedTheme={themeFilter}
              onThemeClick={handleThemeClick}
            />
          ))}
        </div>
      </section>
    </div>
  );
}
