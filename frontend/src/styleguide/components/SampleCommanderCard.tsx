import { ColorIdentityStrip } from '../../components/ColorIdentityStrip';
import type { SampleCommander } from '../data/sampleCommanders';

interface SampleCommanderCardProps {
  commander: SampleCommander;
}

export function SampleCommanderCard({ commander }: SampleCommanderCardProps) {
  return (
    <div className="relative aspect-card overflow-hidden rounded bg-surface-raised">
      {commander.image_url && (
        <img
          src={commander.image_url}
          alt={commander.name}
          className="h-full w-full object-cover"
        />
      )}

      <div className="absolute inset-x-0 top-0">
        <ColorIdentityStrip colorIdentity={commander.color_identity} />
      </div>

      <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-surface-base via-surface-base/70 to-transparent p-3 pt-8">
        <p className="text-sm font-medium text-ink-primary">{commander.name}</p>
      </div>
    </div>
  );
}
