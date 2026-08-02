import { Button } from '../../components/Button';

// Hover/active are transient and can't be permanently shown in a static
// page — documented in words here, with the one state that IS static
// (disabled) shown for real. Applies globally via tokens.css's base
// layer to every <button> and to any label immediately before a file
// input (e.g. UploadSection's "Upload CSV") — not a per-component style.
export function InteractionStates() {
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-6">
        <Button type="button">Default</Button>
        <Button type="button" disabled>
          Disabled
        </Button>
      </div>

      <ul className="list-disc pl-5 text-sm text-ink-secondary">
        <li>Resting: full opacity, pointer cursor</li>
        <li>Hover: opacity 0.9</li>
        <li>Active/pressed: opacity 0.75, scale(0.98)</li>
        <li>Disabled: opacity 0.5, cursor not-allowed (shown above, static)</li>
        <li>Respects prefers-reduced-motion (transition removed, not the state itself)</li>
      </ul>
    </section>
  );
}
