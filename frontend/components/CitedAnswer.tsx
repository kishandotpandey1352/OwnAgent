"use client";

import type { WebPublicCitation } from "@/lib/api";

interface CitedAnswerProps {
  text: string;
  citations?: WebPublicCitation[];
}

const WEB_SOURCE_PATTERN = /(\[Web Source\s+\d+\])/g;

function citationMap(citations: WebPublicCitation[]) {
  return new Map(
    citations.map((citation) => [citation.source_number, citation]),
  );
}

export function CitedAnswer({ text, citations = [] }: CitedAnswerProps) {
  const sources = citationMap(citations);
  const parts = text.split(WEB_SOURCE_PATTERN);

  return (
    <div className="whitespace-pre-wrap text-sm leading-7 text-slate-200">
      {parts.map((part, index) => {
        const match = part.match(/^\[Web Source\s+(\d+)\]$/);
        const citation = match ? sources.get(Number(match[1])) : undefined;

        if (!match || !citation) {
          return <span key={`${index}-${part.slice(0, 12)}`}>{part}</span>;
        }

        return (
          <a
            key={`${index}-${citation.source_number}`}
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="mx-0.5 inline-flex rounded-md border border-cyan-300/30 bg-cyan-300/10 px-1.5 py-0.5 align-baseline text-xs font-semibold text-cyan-100 underline decoration-cyan-200/60 underline-offset-2 transition hover:border-cyan-200/60 hover:bg-cyan-300/20"
            aria-label={`Open web source ${citation.source_number}: ${citation.title}`}
          >
            {part}
          </a>
        );
      })}
    </div>
  );
}
