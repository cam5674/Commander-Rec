interface SwatchToken {
  name: string;
  hex: string;
  className: string;
  contrastNote: string;
}

const SURFACE_TOKENS: SwatchToken[] = [
  { name: 'surface-base', hex: '#121317', className: 'bg-surface-base', contrastNote: 'page background' },
  { name: 'surface-raised', hex: '#1c1e25', className: 'bg-surface-raised', contrastNote: 'cards, panels, modals' },
  { name: 'surface-overlay', hex: '#262932', className: 'bg-surface-overlay', contrastNote: 'popovers, tooltips' },
];

const LINE_TOKENS: SwatchToken[] = [
  { name: 'line-subtle', hex: '#2a2d35', className: 'bg-line-subtle', contrastNote: '1.35:1 on base — decorative only' },
  { name: 'line-default', hex: '#4a4d58', className: 'bg-line-default', contrastNote: '2.20:1 on base — decorative only' },
];

const INK_TOKENS: SwatchToken[] = [
  { name: 'ink-primary', hex: '#f2f1ed', className: 'bg-ink-primary', contrastNote: '16.42:1 on base — AAA' },
  { name: 'ink-secondary', hex: '#a8abb3', className: 'bg-ink-secondary', contrastNote: '8.08:1 on base — AAA' },
  { name: 'ink-muted', hex: '#7d818a', className: 'bg-ink-muted', contrastNote: '4.76:1 on base — AA (large/decorative only on raised)' },
];

const MANA_TOKENS: SwatchToken[] = [
  { name: 'mana-white', hex: '#f4ecd8', className: 'bg-mana-white', contrastNote: '15.48:1 glyph — AAA' },
  { name: 'mana-blue', hex: '#2b6cac', className: 'bg-mana-blue', contrastNote: '4.83:1 glyph — AA' },
  { name: 'mana-black', hex: '#6f5e7b', className: 'bg-mana-black', contrastNote: '5.21:1 glyph — AA' },
  { name: 'mana-red', hex: '#c33f35', className: 'bg-mana-red', contrastNote: '4.55:1 glyph — AA' },
  { name: 'mana-green', hex: '#3f9142', className: 'bg-mana-green', contrastNote: '4.64:1 glyph — AA' },
  { name: 'mana-colorless', hex: '#9a9ba0', className: 'bg-mana-colorless', contrastNote: '6.57:1 glyph — AAA' },
  { name: 'mana-gold', hex: '#c9a349', className: 'bg-mana-gold', contrastNote: '7.66:1 glyph — AAA' },
];

function SwatchRow({ tokens }: { tokens: SwatchToken[] }) {
  return (
    <div className="flex flex-wrap gap-4">
      {tokens.map((token) => (
        <div key={token.name} className="w-40">
          <div className={`h-16 w-full rounded ring-1 ring-line-default ${token.className}`} />
          <p className="mt-2 text-sm font-medium text-ink-primary">{token.name}</p>
          <p className="text-xs text-ink-secondary">{token.hex}</p>
          <p className="text-xs text-ink-muted">{token.contrastNote}</p>
        </div>
      ))}
    </div>
  );
}

export function ColorSwatches() {
  return (
    <section className="flex flex-col gap-8">
      <div>
        <h3 className="mb-3 text-lg font-semibold text-ink-primary">Surfaces</h3>
        <SwatchRow tokens={SURFACE_TOKENS} />
      </div>
      <div>
        <h3 className="mb-3 text-lg font-semibold text-ink-primary">Lines</h3>
        <SwatchRow tokens={LINE_TOKENS} />
      </div>
      <div>
        <h3 className="mb-3 text-lg font-semibold text-ink-primary">Ink (text)</h3>
        <SwatchRow tokens={INK_TOKENS} />
      </div>
      <div>
        <h3 className="mb-3 text-lg font-semibold text-ink-primary">Mana (color identity)</h3>
        <SwatchRow tokens={MANA_TOKENS} />
      </div>
      <div>
        <h3 className="mb-3 text-lg font-semibold text-ink-primary">
          Brand action vs. mana-gold (must stay visually distinct)
        </h3>
        <div className="flex flex-wrap items-center gap-6">
          <button
            type="button"
            className="rounded bg-brand-action px-4 py-2 text-sm font-semibold text-ink-on-mana"
          >
            Primary button (brand-action)
          </button>
          <a href="#" className="text-sm font-medium text-brand-action underline">
            Link example (brand-action)
          </a>
          <div className="w-40">
            <div className="h-16 w-full rounded ring-1 ring-line-default bg-mana-gold" />
            <p className="mt-2 text-sm font-medium text-ink-primary">mana-gold</p>
            <p className="text-xs text-ink-secondary">#c9a349 — color-identity use only</p>
          </div>
        </div>
      </div>
    </section>
  );
}
