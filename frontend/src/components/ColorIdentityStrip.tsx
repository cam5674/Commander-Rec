interface ColorIdentityStripProps {
  colorIdentity: string[];
}

const MANA_FILL: Record<string, string> = {
  W: 'bg-mana-white',
  U: 'bg-mana-blue',
  B: 'bg-mana-black',
  R: 'bg-mana-red',
  G: 'bg-mana-green',
};

const MANA_LABEL: Record<string, string> = {
  W: 'White',
  U: 'Blue',
  B: 'Black',
  R: 'Red',
  G: 'Green',
};

// Per-segment text color, chosen per mana fill so the WUBRG letter itself
// clears AA (4.5:1) against its own background — verified against the
// actual token values in tokens.css, not assumed:
//   W ink-on-mana 15.48:1 · U ink-primary 4.83:1 · B ink-primary 5.21:1
//   R ink-primary 4.55:1 · G ink-on-mana 4.64:1 · colorless ink-on-mana 6.57:1
// Both text colors are existing tokens (no new values introduced).
const MANA_TEXT: Record<string, string> = {
  W: 'text-ink-on-mana',
  U: 'text-ink-primary',
  B: 'text-ink-primary',
  R: 'text-ink-primary',
  G: 'text-ink-on-mana',
};

// A thin proportional strip with a letter per segment — color is never the
// only signal for color identity (adjacent WUBRG hues can sit within ~1:1
// contrast of each other, indistinguishable for colorblind users without
// this). Segment dividers use surface-base, which clears the 3:1
// non-text/graphical-object minimum against every mana fill, so segment
// boundaries are visible even when two adjacent hues read as near-identical.
export function ColorIdentityStrip({ colorIdentity }: ColorIdentityStripProps) {
  const isColorless = colorIdentity.length === 0;
  const label = isColorless
    ? 'Color identity: Colorless'
    : `Color identity: ${colorIdentity.map((color) => MANA_LABEL[color] ?? color).join(', ')}`;

  return (
    <div role="img" aria-label={label} className="flex h-6 w-full overflow-hidden rounded">
      {isColorless ? (
        <span
          aria-hidden="true"
          className="flex h-full flex-1 items-center justify-center bg-mana-colorless text-xs font-semibold text-ink-on-mana"
        >
          C
        </span>
      ) : (
        colorIdentity.map((color, index) => (
          <span
            key={`${color}-${index}`}
            aria-hidden="true"
            className={`flex h-full flex-1 items-center justify-center text-xs font-semibold ${
              MANA_FILL[color] ?? 'bg-mana-colorless'
            } ${MANA_TEXT[color] ?? 'text-ink-on-mana'} ${
              index < colorIdentity.length - 1 ? 'border-r border-surface-base' : ''
            }`}
          >
            {color}
          </span>
        ))
      )}
    </div>
  );
}
