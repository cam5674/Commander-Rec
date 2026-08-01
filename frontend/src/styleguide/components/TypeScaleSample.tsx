interface TypeStep {
  className: string;
  size: string;
  useCase: string;
}

const TYPE_STEPS: TypeStep[] = [
  { className: 'text-xs', size: '12px', useCase: 'fine print, badge captions, timestamps' },
  { className: 'text-sm', size: '14px', useCase: 'secondary metadata, form hints, card stat lines' },
  { className: 'text-base', size: '16px', useCase: 'body copy, card names in lists, form inputs' },
  { className: 'text-lg', size: '18px', useCase: 'subheadings' },
  { className: 'text-xl', size: '20px', useCase: 'panel/modal titles' },
  { className: 'text-2xl', size: '24px', useCase: 'page-section headings' },
  { className: 'text-3xl', size: '30px', useCase: 'page title (may use font-display)' },
  { className: 'text-4xl', size: '36px', useCase: 'app wordmark only (font-display)' },
];

export function TypeScaleSample() {
  return (
    <section className="flex flex-col gap-3">
      {TYPE_STEPS.map((step) => (
        <div key={step.className} className="flex flex-wrap items-baseline gap-3">
          <p className={`${step.className} text-ink-primary`}>Commander Recommender</p>
          <span className="text-xs text-ink-muted">
            {step.className} · {step.size} · {step.useCase}
          </span>
        </div>
      ))}
    </section>
  );
}
