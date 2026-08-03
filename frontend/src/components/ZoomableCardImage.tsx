import { useEffect, useRef, useState } from 'react';
import { toArtCropUrl, toLargeUrl } from '../content/scryfallImage';
import { ColorIdentityStrip } from './ColorIdentityStrip';

interface ZoomableCardImageProps {
  imageUrl: string | null;
  scryfallUrl: string;
  name: string;
  colorIdentity: string[];
}

interface OverlayPosition {
  top: number;
  left: number;
}

const OVERLAY_WIDTH = 280;
const OVERLAY_HEIGHT = (OVERLAY_WIDTH * 7) / 5; // matches --aspect-card
const OVERLAY_GAP = 12;
const VIEWPORT_MARGIN = 8;

function computePosition(triggerRect: DOMRect): OverlayPosition {
  let left = triggerRect.right + OVERLAY_GAP;
  if (left + OVERLAY_WIDTH > window.innerWidth - VIEWPORT_MARGIN) {
    left = triggerRect.left - OVERLAY_GAP - OVERLAY_WIDTH;
  }
  left = Math.max(VIEWPORT_MARGIN, Math.min(left, window.innerWidth - OVERLAY_WIDTH - VIEWPORT_MARGIN));

  let top = triggerRect.top;
  if (top + OVERLAY_HEIGHT > window.innerHeight - VIEWPORT_MARGIN) {
    top = window.innerHeight - OVERLAY_HEIGHT - VIEWPORT_MARGIN;
  }
  top = Math.max(VIEWPORT_MARGIN, top);

  return { top, left };
}

// Split by interaction target: the image itself is hover-to-preview on
// desktop and tap-the-icon on touch (no hover). The rest of a
// RecommendationCard (name/badges/"Show details") has its own separate
// click handling untouched by this component — see report.
export function ZoomableCardImage({ imageUrl, scryfallUrl, name, colorIdentity }: ZoomableCardImageProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<OverlayPosition | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const open = () => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) {
      return;
    }
    setPosition(computePosition(rect));
    setIsOpen(true);
    requestAnimationFrame(() => setIsVisible(true));
  };

  const close = () => {
    setIsVisible(false);
    setIsOpen(false);
  };

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        close();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  if (!imageUrl) {
    return (
      <div className="w-32 shrink-0">
        <div className="aspect-art overflow-hidden rounded bg-surface-overlay" />
        <div className="mt-1 overflow-hidden rounded">
          <ColorIdentityStrip colorIdentity={colorIdentity} />
        </div>
      </div>
    );
  }

  return (
    <div className="w-32 shrink-0">
      <div
        ref={containerRef}
        className="group relative aspect-art overflow-hidden rounded bg-surface-overlay"
        onMouseEnter={open}
        onMouseLeave={close}
      >
        <a
          href={scryfallUrl}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={`View ${name} on Scryfall`}
          className="block h-full w-full focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-brand-action"
        >
          <img src={toArtCropUrl(imageUrl)} alt={name} className="h-full w-full object-cover" />
        </a>

        {/* Hidden by default, revealed on hover (desktop) or always shown
            on touch devices, which have no hover state to reveal it. */}
        <button
          type="button"
          onClick={(event) => {
            event.stopPropagation();
            open();
          }}
          aria-label={`View full-size image of ${name}`}
          className="absolute bottom-1 right-1 rounded bg-surface-base/80 p-1 opacity-0 transition-opacity duration-150 group-hover:opacity-100 focus-visible:opacity-100 motion-reduce:transition-none [@media(hover:none)]:opacity-100"
        >
          <svg aria-hidden="true" viewBox="0 0 20 20" className="h-3.5 w-3.5 fill-none stroke-ink-primary stroke-2">
            <circle cx="8.5" cy="8.5" r="5.5" />
            <line x1="16.5" y1="16.5" x2="12.5" y2="12.5" />
          </svg>
        </button>
      </div>

      <div className="mt-1 overflow-hidden rounded">
        <ColorIdentityStrip colorIdentity={colorIdentity} />
      </div>

      {isOpen && position && (
        // pointer-events-none on hover-capable devices — this full-viewport
        // layer exists only to catch outside-taps on touch. On desktop it
        // must stay click-through, otherwise it covers the trigger the
        // instant it mounts and steals the hover straight back off it,
        // firing mouseleave a frame after mouseenter (the "flashes and
        // instantly closes" bug).
        <div
          className="fixed inset-0 z-40 pointer-events-none [@media(hover:none)]:pointer-events-auto"
          onClick={close}
        >
          <div
            className={`fixed z-50 overflow-hidden rounded shadow-lg motion-safe:transition-opacity motion-safe:duration-150 ${
              isVisible ? 'opacity-100' : 'opacity-0'
            }`}
            style={{ top: position.top, left: position.left, width: OVERLAY_WIDTH }}
            onClick={(event) => event.stopPropagation()}
          >
            <img src={toLargeUrl(imageUrl)} alt={name} className="block w-full" />
            {/* Close control — only needed on touch, where there's no
                mouse-leave to dismiss the overlay. */}
            <button
              type="button"
              onClick={close}
              aria-label="Close full-size image"
              className="absolute right-1 top-1 hidden rounded-full bg-surface-base/80 px-1.5 py-0.5 text-xs text-ink-primary [@media(hover:none)]:block"
            >
              ✕
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
