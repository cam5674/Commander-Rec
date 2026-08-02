interface HeaderProps {
  centered?: boolean;
}

export function Header({ centered = false }: HeaderProps) {
  return (
    <header
      className={`border-b border-line-default pb-4 ${centered ? 'text-center' : ''}`}
    >
      <h1 className="font-display text-4xl">MTG Commander Recommender</h1>
      <p className="mt-2 text-base text-ink-secondary">
        Upload your card collection to find commanders that fit the themes you
        already own.
      </p>
    </header>
  );
}
