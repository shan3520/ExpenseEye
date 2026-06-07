import type { ComponentType, ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

/** Shared module states — keeps every analytics panel visually consistent. */

export function Loading({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center gap-3 py-12 text-sm text-txt-faint" role="status" aria-live="polite">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-line-strong border-t-brand motion-reduce:animate-none motion-reduce:border-brand" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-md border border-danger/25 bg-danger/[0.08] p-4 text-sm text-danger">
      <AlertCircle className="mt-0.5 h-4 w-4 flex-shrink-0 text-danger" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}

export function Empty({
  icon: Icon,
  title,
  children,
}: {
  icon: ComponentType<{ className?: string }>;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="state-block">
      <Icon className="mx-auto mb-3 h-8 w-8 text-txt-faint" aria-hidden="true" />
      <p className="text-base font-medium text-txt">{title}</p>
      {children && <p className="mx-auto mt-1.5 max-w-md text-sm text-txt-muted">{children}</p>}
    </div>
  );
}
