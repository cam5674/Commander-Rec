// Scryfall's image CDN serves multiple crops of the same card at predictable
// URLs that differ only in this one path segment (png/border_crop/art_crop/
// large/normal/small) — see https://scryfall.com/docs/api/images. The
// backend only stores the "normal" (full card) URL, so the art-only crop is
// derived here rather than requiring a backend change.
export function toArtCropUrl(imageUrl: string): string {
  return imageUrl.replace('/normal/', '/art_crop/');
}

// Verified 672x936 — matches the --aspect-card token (5/7) closely enough
// to use directly. Used for the full-size zoom view, where the embedded
// rules text (illegible on the art-crop thumbnail) becomes readable.
export function toLargeUrl(imageUrl: string): string {
  return imageUrl.replace('/normal/', '/large/');
}
