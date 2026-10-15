export function BrandMark({ className = "h-8 w-8" }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" className={className} aria-hidden>
      <rect width="64" height="64" rx="16" fill="hsl(var(--accent))" />
      <path d="M16 46V18h6l20 20V18h6v28h-6L22 26v20z" fill="hsl(var(--primary))" />
    </svg>
  );
}
