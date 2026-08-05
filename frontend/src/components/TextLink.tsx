import type { ButtonHTMLAttributes } from 'react';

// Shared treatment for underlined, brand-colored text triggers — pulled out
// once a second spot (the sample-collection trigger) needed the same look
// as the theme-filter "Clear" control, instead of copying the class list a
// third time. The commander name's Scryfall anchor and the supporting-card
// pill links stay separate — different element (anchor, not button) and
// different color/hover logic tied to external navigation, not just a
// copy-paste variant of this.
export function TextLink({ className = '', ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      className={`font-medium text-brand-action underline underline-offset-2 ${className}`}
      {...props}
    />
  );
}
