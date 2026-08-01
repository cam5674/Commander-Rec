import { ColorSwatches } from './components/ColorSwatches';
import { TypeScaleSample } from './components/TypeScaleSample';
import { SpacingSample } from './components/SpacingSample';
import { RecommendationCard } from '../components/RecommendationCard';
import { SAMPLE_COMMANDERS } from './data/sampleCommanders';

export function StyleGuidePage() {
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
        <h2 className="mb-4 text-2xl font-semibold">Sample commanders</h2>
        <p className="mb-4 text-sm text-ink-secondary">
          Rendered with the real RecommendationCard component, not a lookalike demo.
        </p>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-7">
          {SAMPLE_COMMANDERS.map((commander) => (
            <RecommendationCard key={commander.name} {...commander} />
          ))}
        </div>
      </section>
    </div>
  );
}
