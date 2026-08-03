import { useEffect, useRef, useState, type ReactNode } from 'react';
import { toLargeUrl } from '../content/scryfallImage';

interface CardHoverPreviewProps {
  imageUrl: string | null;
  name: string;
  children: ReactNode;
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

// Mouse hover + keyboard focus only — deliberately not touch. A touch tap on
// the wrapped link fires a synthetic hover-then-click in quick succession,
// which would just flash the preview before navigating away; touch users get
// the original tap-to-navigate behavior unchanged instead.
export function CardHoverPreview({ imageUrl, name, children }: CardHoverPreviewProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [position, setPosition] = useState<OverlayPosition | null>(null);
  const triggerRef = useRef<HTMLSpanElement>(null);

  const open = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
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
    return <>{children}</>;
  }

  return (
    <span
      ref={triggerRef}
      className="relative inline-block"
      onMouseEnter={open}
      onMouseLeave={close}
      onFocus={open}
      onBlur={close}
    >
      {children}

      {isOpen && position && (
        // aria-hidden — purely a visual enhancement layered over a link
        // whose accessible name already identifies the card; without this,
        // the preview's own alt text would announce the same name again.
        <div
          aria-hidden="true"
          className={`pointer-events-none fixed z-50 overflow-hidden rounded shadow-lg motion-safe:transition-opacity motion-safe:duration-150 motion-reduce:transition-none ${
            isVisible ? 'opacity-100' : 'opacity-0'
          }`}
          style={{ top: position.top, left: position.left, width: OVERLAY_WIDTH }}
        >
          <img src={toLargeUrl(imageUrl)} alt={name} className="block w-full" />
        </div>
      )}
    </span>
  );
}
