import React from 'react';
import { itsmKbUrl } from '../lib/itsm';

// Renders "KB 22 ↗" as an external link when kbId is present, plain text
// otherwise. Click opens the ITSM's KB page in a new tab.
export function KbLink({
  kbId,
  className = '',
}: {
  kbId: string | number | null | undefined;
  className?: string;
}) {
  const url = itsmKbUrl(kbId);
  if (!url) return <span className={className}>KB —</span>;
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`hover:underline ${className}`}
      title={`Open KB ${kbId} in the ITSM (opens new tab)`}
      onClick={(e) => e.stopPropagation()}
    >
      KB {kbId}{' '}
      <span className="text-[10px] opacity-70" aria-hidden>
        ↗
      </span>
    </a>
  );
}
