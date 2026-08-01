import { ColorIdentityStrip } from './ColorIdentityStrip';
import type { CommanderRecommendation } from '../types/api';

export type RecommendationCardProps = Pick<CommanderRecommendation, 'name' | 'image_url' | 'color_identity'>;

export function RecommendationCard({ name, image_url, color_identity }: RecommendationCardProps) {
  return (
    <div className="relative aspect-card overflow-hidden rounded bg-surface-raised">
      {image_url && <img src={image_url} alt={name} className="h-full w-full object-cover" />}

      <div className="absolute inset-x-0 top-0">
        <ColorIdentityStrip colorIdentity={color_identity} />
      </div>

      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-surface-base via-surface-base/70 to-transparent p-3 pt-8">
        <p className="text-sm font-medium text-ink-primary">{name}</p>
      </div>
    </div>
  );
}
