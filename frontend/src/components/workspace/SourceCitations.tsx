"use client";

import { useState, type CSSProperties } from "react";
import type { Source } from "@/lib/types";
import Icon from "@/components/ui/Icon";

function scoreTone(score: number): string {
  if (score >= 0.75) return "bg-emerald-500";
  if (score >= 0.55) return "bg-brand-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-muted-foreground/50";
}

function scoreLabel(score: number): string {
  if (score >= 0.75) return "Strong match";
  if (score >= 0.55) return "Good match";
  if (score >= 0.4) return "Weak match";
  return "Distant match";
}

/**
 * Inline citations shown under an answer. The evidence rail takes over at the
 * `xl` breakpoint, so this is hidden there to avoid showing the same sources
 * twice.
 */
export default function SourceCitations({ sources }: { sources: Source[] }) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  if (sources.length === 0) return null;

  return (
    <div className="mt-4 border-t border-line pt-3.5 xl:hidden">
      <p className="mb-2.5 flex items-center gap-1.5 text-[0.6875rem] font-semibold tracking-[0.12em] text-muted-foreground uppercase">
        <Icon name="quote" className="size-3.5" />
        Sources
      </p>
      <ul className="stagger space-y-1.5">
        {sources.map((source, index) => {
          const open = openIndex === index;
          const percent = Math.round(Math.min(Math.max(source.score, 0), 1) * 100);
          return (
            <li
              key={`${source.document_id}-${source.chunk_index}-${index}`}
              style={{ "--index": index } as CSSProperties}
              className="animate-fade-up overflow-hidden rounded-xl border border-line bg-muted/50 transition-colors duration-300 hover:border-line-strong"
            >
              <button
                type="button"
                onClick={() => setOpenIndex(open ? null : index)}
                className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
                aria-expanded={open}
              >
                <Icon
                  name="file"
                  className="size-3.5 shrink-0 text-brand-600 dark:text-brand-400"
                />
                <span className="truncate text-xs font-medium">
                  {source.filename}
                </span>
                <span className="chip shrink-0 py-0.5">p.{source.page}</span>
                <span
                  className="ml-auto flex shrink-0 items-center gap-1.5"
                  title={`${scoreLabel(source.score)} — ${percent}% similarity`}
                >
                  <span className="h-1 w-8 overflow-hidden rounded-full bg-line">
                    <span
                      className={`block h-full rounded-full transition-[width] duration-700 ease-out ${scoreTone(source.score)}`}
                      style={{ width: `${percent}%` }}
                    />
                  </span>
                  <span className="tabular-nums text-[0.6875rem] text-muted-foreground">
                    {percent}%
                  </span>
                </span>
                <Icon
                  name="chevronDown"
                  className={`size-3.5 shrink-0 text-muted-foreground transition-transform duration-300 ${
                    open ? "rotate-180" : ""
                  }`}
                />
              </button>
              <div className="disclosure" data-open={open}>
                <p className="border-t border-line px-3 py-2.5 text-xs leading-relaxed text-muted-foreground">
                  {source.snippet}
                </p>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
