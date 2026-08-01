// Tailwind's scanner needs literal class strings in source — a template
// literal like `h-${step}` would never be picked up and generated.
const SPACING_STEPS: { step: number; px: number; heightClass: string }[] = [
  { step: 1, px: 4, heightClass: 'h-1' },
  { step: 2, px: 8, heightClass: 'h-2' },
  { step: 3, px: 12, heightClass: 'h-3' },
  { step: 4, px: 16, heightClass: 'h-4' },
  { step: 6, px: 24, heightClass: 'h-6' },
  { step: 8, px: 32, heightClass: 'h-8' },
  { step: 12, px: 48, heightClass: 'h-12' },
  { step: 16, px: 64, heightClass: 'h-16' },
];

export function SpacingSample() {
  return (
    <section className="flex flex-wrap items-end gap-4">
      {SPACING_STEPS.map(({ step, px, heightClass }) => (
        <div key={step} className="flex flex-col items-center gap-2">
          <div className={`w-8 bg-brand-action ${heightClass}`} />
          <span className="text-xs text-ink-muted">
            {step} · {px}px
          </span>
        </div>
      ))}
    </section>
  );
}
