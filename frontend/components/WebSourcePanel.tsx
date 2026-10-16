"use client";

import { useMemo, useState } from "react";
import type {
  PublicWebResearchSummary,
  WebPublicCitation,
  WebPublicFinancialFact,
} from "@/lib/api";

interface WebSourcePanelProps {
  research: PublicWebResearchSummary;
}

type CitationGroup = {
  key: string;
  url: string;
  title: string;
  domain: string;
  trustTier?: string | null;
  contentType?: string | null;
  retrievedAt?: string | null;
  pageNumber?: number | null;
  citations: WebPublicCitation[];
};

const TRUST_PRIORITY: Record<string, number> = {
  public_authority: 5,
  trusted_domain: 4,
  finance_candidate: 3,
  general_web: 2,
  low_trust: 1,
};

function cleanText(value?: string | null) {
  return value?.replace(/\s+/g, " ").trim() ?? "";
}

function conciseSnippet(value?: string | null, maxLength = 220) {
  const cleaned = cleanText(value);
  if (!cleaned || cleaned.length <= maxLength) return cleaned;
  const candidate = cleaned.slice(0, maxLength);
  const lastSentence = Math.max(candidate.lastIndexOf(". "), candidate.lastIndexOf("; "));
  if (lastSentence > 90) return candidate.slice(0, lastSentence + 1);
  const lastSpace = candidate.lastIndexOf(" ");
  return `${candidate.slice(0, lastSpace > 0 ? lastSpace : maxLength)}…`;
}

function trustPriority(value?: string | null) {
  return value ? TRUST_PRIORITY[value] ?? 0 : 0;
}

function formatTrustTier(value?: string | null) {
  return value
    ? value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase())
    : null;
}

function formatRetrievedAt(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toLocaleString();
}

function groupCitations(citations: WebPublicCitation[]): CitationGroup[] {
  const groups = new Map<string, CitationGroup>();
  for (const citation of citations) {
    const key = citation.url || `${citation.domain}:${citation.title}`;
    const existing = groups.get(key);
    if (existing) {
      existing.citations.push(citation);
      continue;
    }
    groups.set(key, {
      key,
      url: citation.url,
      title: citation.title,
      domain: citation.domain,
      trustTier: citation.trust_tier,
      contentType: citation.content_type,
      retrievedAt: citation.retrieved_at,
      pageNumber: citation.page_number,
      citations: [citation],
    });
  }
  return Array.from(groups.values()).sort(
    (left, right) => trustPriority(right.trustTier) - trustPriority(left.trustTier),
  );
}

function factValue(fact: WebPublicFinancialFact) {
  const value = fact.raw_value ?? fact.normalized_numeric_value ?? fact.numeric_value;
  if (value === null || value === undefined || value === "") return null;
  if (fact.raw_value) return `${fact.raw_value}${fact.scale ? ` ${fact.scale}` : ""}`;
  return [fact.currency, value, fact.scale, fact.unit_label].filter(Boolean).join(" ");
}

function WebSourceLink({ citation }: { citation: WebPublicCitation }) {
  return (
    <a
      href={citation.url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={(event) => event.stopPropagation()}
      className="inline-flex rounded-md border border-cyan-300/25 bg-cyan-300/10 px-1.5 py-0.5 text-[10px] font-semibold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-300/20"
    >
      [Web Source {citation.source_number}]
    </a>
  );
}

function ValidatedFactCard({
  fact,
  citation,
}: {
  fact: WebPublicFinancialFact;
  citation?: WebPublicCitation;
}) {
  const value = factValue(fact);
  const validation = typeof fact.validation_score === "number"
    ? `${Math.round(fact.validation_score * 100)}%`
    : null;
  return (
    <div className="rounded-xl border border-emerald-300/20 bg-emerald-300/[0.05] px-3 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-white">{fact.metric_label}</p>
          {value ? <p className="mt-1 text-base font-semibold text-emerald-100">{value}</p> : null}
        </div>
        <span className="rounded-full border border-emerald-300/25 bg-emerald-300/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-100">Validated fact</span>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-slate-400">
        {fact.period_label ? <span>{fact.period_label}</span> : null}
        {validation ? <span>· Validation {validation}</span> : null}
        {citation ? <WebSourceLink citation={citation} /> : null}
      </div>
    </div>
  );
}

function SourceGroupCard({ group }: { group: CitationGroup }) {
  const primary = group.citations[0];
  const trustTier = formatTrustTier(group.trustTier);
  const retrievedAt = formatRetrievedAt(group.retrievedAt);
  return (
    <details className="group rounded-xl border border-white/10 bg-black/20">
      <summary className="cursor-pointer list-none px-3 py-2.5">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5">
              {group.citations.map((citation) => <WebSourceLink key={citation.source_number} citation={citation} />)}
              <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-[9px] font-semibold text-cyan-100">Web-derived</span>
            </div>
            <p className="mt-2 truncate text-xs font-semibold text-white">{group.title}</p>
            <p className="mt-0.5 truncate text-[10px] text-slate-500">{group.domain}{trustTier ? ` · ${trustTier}` : ""}</p>
          </div>
          <span className="shrink-0 text-sm text-slate-500 transition-transform group-open:rotate-180">▾</span>
        </div>
      </summary>
      <div className="border-t border-white/10 px-3 pb-3 pt-2.5">
        <div className="flex flex-wrap gap-2 text-[10px] text-slate-500">
          {group.pageNumber ? <span>Page {group.pageNumber}</span> : null}
          {group.contentType ? <span>{group.contentType.toUpperCase()}</span> : null}
          {retrievedAt ? <span>Retrieved {retrievedAt}</span> : null}
        </div>
        {group.citations.map((citation) => citation.snippet ? (
          <div key={`snippet-${citation.source_number}`} className="mt-2 rounded-lg bg-white/[0.03] p-2.5">
            <p className="text-[10px] font-semibold text-cyan-200">Web Source {citation.source_number}</p>
            <p className="mt-1 text-xs leading-5 text-slate-400">{conciseSnippet(citation.snippet, 380)}</p>
          </div>
        ) : null)}
        <a href={primary.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex text-[11px] font-semibold text-cyan-200 hover:text-cyan-100 hover:underline">Open source ↗</a>
      </div>
    </details>
  );
}

export function WebSourcePanel({ research }: WebSourcePanelProps) {
  const [open, setOpen] = useState(true);
  const [showAllSources, setShowAllSources] = useState(false);
  const citations = research.citations ?? [];
  const facts = research.validated_facts ?? [];
  const groups = useMemo(() => groupCitations(citations), [citations]);
  const citationByNumber = useMemo(
    () => new Map(citations.map((citation) => [citation.source_number, citation])),
    [citations],
  );
  if (!groups.length && !facts.length) return null;

  const summaryGroups = groups.slice(0, 3);
  const visibleGroups = showAllSources ? groups : groups.slice(0, 3);
  return (
    <section className="overflow-hidden rounded-2xl border border-cyan-300/20 bg-slate-950/80 shadow-lg shadow-black/10">
      <button type="button" onClick={() => setOpen((current) => !current)} className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left transition hover:bg-white/[0.03]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-200/80">Web summary</p>
            <span className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-100">{citations.length} source{citations.length === 1 ? "" : "s"}</span>
            {facts.length ? <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-100">{facts.length} validated</span> : null}
          </div>
          <p className="mt-1 text-xs text-slate-400">Short highlights from external evidence.</p>
        </div>
        <span className={`shrink-0 text-lg text-slate-400 transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>
      {open ? <div className="border-t border-white/10 p-4">
        {summaryGroups.length ? <div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-cyan-200/70">What the web sources say</p>
          <div className="mt-2 space-y-2">
            {summaryGroups.map((group) => {
              const citation = group.citations[0];
              return <div key={`summary-${group.key}`} className="flex gap-2"><span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-cyan-300/70" /><p className="text-xs leading-5 text-slate-300"><span className="font-semibold text-slate-100">{group.domain}:</span>{" "}{conciseSnippet(citation.snippet, 190)}{" "}<WebSourceLink citation={citation} /></p></div>;
            })}
          </div>
        </div> : null}
        {facts.length ? <div className="mt-3 space-y-2">{facts.map((fact, index) => <ValidatedFactCard key={`${fact.source_number}-${fact.metric_label}-${index}`} fact={fact} citation={citationByNumber.get(fact.source_number)} />)}</div> : null}
        {groups.length ? <div className="mt-4">
          <div className="mb-2 flex items-center justify-between gap-3"><p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">Source details</p><span className="text-[10px] text-slate-600">Click a source to expand</span></div>
          <div className="space-y-2">{visibleGroups.map((group) => <SourceGroupCard key={group.key} group={group} />)}</div>
          {groups.length > 3 ? <button type="button" onClick={() => setShowAllSources((current) => !current)} className="mt-3 text-xs font-semibold text-cyan-200 transition hover:text-cyan-100">{showAllSources ? "Show fewer sources" : `Show ${groups.length - 3} more source${groups.length - 3 === 1 ? "" : "s"}`}</button> : null}
        </div> : null}
      </div> : null}
    </section>
  );
}
