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

// A thin proportional strip rather than overlaid pips — same color-identity
// information, without visually competing with the card art underneath it.
// Relies on a clipping container (overflow-hidden + rounded) to match the
// card's corners; this component just fills the strip's own bounds.
export function ColorIdentityStrip({ colorIdentity }: ColorIdentityStripProps) {
  const isColorless = colorIdentity.length === 0;
  const label = isColorless
    ? 'Color identity: Colorless'
    : `Color identity: ${colorIdentity.map((color) => MANA_LABEL[color] ?? color).join(', ')}`;

  return (
    <div role="img" aria-label={label} className="flex h-2 w-full">
      {isColorless ? (
        <span aria-hidden="true" className="h-full flex-1 bg-mana-colorless" />
      ) : (
        colorIdentity.map((color, index) => (
          <span
            key={`${color}-${index}`}
            aria-hidden="true"
            className={`h-full flex-1 ${MANA_FILL[color] ?? 'bg-mana-colorless'}`}
          />
        ))
      )}
    </div>
  );
}
