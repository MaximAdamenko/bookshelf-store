import type { ReactNode } from "react";

export function SkeletonBlock({ className = "h-64" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-stone-200 ${className}`} />;
}

export function SkeletonList({ rows = 4, className = "h-16" }: { rows?: number; className?: string }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <SkeletonBlock key={i} className={className} />
      ))}
    </div>
  );
}

export function SkeletonGrid({ cards = 8 }: { cards?: number }) {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {Array.from({ length: cards }, (_, i) => (
        <SkeletonBlock key={i} className="h-80" />
      ))}
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return <div className="py-16 text-center text-sm text-red-700">{message}</div>;
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="py-16 text-center">
      <p className="text-lg font-medium text-stone-700">{title}</p>
      {hint && <p className="mt-1 text-sm text-stone-500">{hint}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
