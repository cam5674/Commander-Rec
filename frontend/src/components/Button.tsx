import type { ButtonHTMLAttributes } from 'react';

// The one button style repeated identically across the app (submit,
// reset, style-guide demo). "Show details" and the zoom/close icon
// buttons are each different enough (text-only, icon-only, specific
// positioning) that folding them into this too would be a premature
// variant system rather than removing real duplication — left as-is.
export function Button({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded bg-brand-action px-4 py-2 text-sm font-semibold text-ink-on-mana disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}
