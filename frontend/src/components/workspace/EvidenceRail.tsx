"use client";

import Icon from "@/components/ui/Icon";
import type { Source } from "@/lib/types";

export type EvidenceTurn = {
  id: string;
  question: string;
  sources: Source[];
};

type Props = {
  turns: EvidenceTurn[];
  activeId: string | null;
  onSelect: (id: string) => void;
};

function scoreTone(score: number): string {
  if (score >= 0.75) return "bg-emerald-500";
  if (score >= 0.55) return "bg-brand-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-muted-foreground/50";
}

/**
 * Persistent panel holding the passages behind the selected answer, so the
 * evidence can be read without expanding a citation inside the transcript.
 */
export default function EvidenceRail({ turns, activeId, onSelect }: Props) {
  const active = turns.find((turn) => turn.id === activeId) ?? turns.at(-1);
  const sources = active?.sources ?? [];

  return (
    <aside className="card hidden w-80 shrink-0 animate-fade-up flex-col overflow-hidden [animation-delay:120ms] xl:flex">
      <header className="flex items-center gap-2 border-b border-line px-4 py-3.5">
        <Icon
          name="bookmark"
          className="size-4 shrink-0 text-brand-600 dark:text-brand-400"
        />
        <h2 className="text-sm font-semibold">Evidence</h2>
        {sources.length > 0 && (
          <span className="chip ml-auto py-0.5 tabular-nums">{sources.length}</span>
        )}
      </header>

      {turns.length > 1 && (
        <div className="flex items-center gap-1.5 border-b border-line px-4 py-2.5">
          <span className="mr-1 text-[0.6875rem] font-medium text-muted-foreground">
            Answer
          </span>
          <div className="flex flex-wrap gap-1">
            {turns.map((turn, index) => {
              const isActive = turn.id === active?.id;
              return (
                <button
                  key={turn.id}
                  type="button"
                  onClick={() => onSelect(turn.id)}
                  aria-current={isActive}
                  className={
                    "grid size-6 place-items-center rounded-md text-[0.6875rem] font-semibold tabular-nums transition-colors " +
                    (isActive
                      ? "bg-brand-600 text-white"
                      : "bg-muted text-muted-foreground hover:bg-line hover:text-foreground")
                  }
                  title={turn.question}
                >
                  {index + 1}
                </button>
              );
            })}
          </div>
        </div>
      )}

      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {sources.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-2.5 px-4 text-center">
            <span className="grid size-10 place-items-center rounded-xl bg-muted text-muted-foreground">
              <Icon name="book" className="size-5" />
            </span>
            <p className="text-sm font-medium">Nothing cited yet</p>
            <p className="text-xs leading-relaxed text-muted-foreground">
              The passages used to build each answer appear here as soon as
              retrieval finishes.
            </p>
          </div>
        ) : (
          <ul className="stagger space-y-2.5">
            {sources.map((source, index) => {
              const percent = Math.round(
                Math.min(Math.max(source.score, 0), 1) * 100,
              );
              return (
                <li
                  key={`${source.document_id}-${source.chunk_index}-${index}`}
                  className="animate-fade-up rounded-xl border border-line bg-muted/40 p-3"
                >
                  <div className="flex items-center gap-2">
                    <Icon
                      name="file"
                      className="size-3.5 shrink-0 text-brand-600 dark:text-brand-400"
                    />
                    <p className="truncate text-xs font-semibold">
                      {source.filename}
                    </p>
                  </div>

                  <div className="mt-2 flex items-center gap-2">
                    <span className="chip py-0.5">Page {source.page}</span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-1 w-full overflow-hidden rounded-full bg-line">
                        <span
                          className={`block h-full rounded-full transition-[width] duration-700 ease-out ${scoreTone(source.score)}`}
                          style={{ width: `${percent}%` }}
                        />
                      </span>
                      <span className="text-[0.6875rem] tabular-nums text-muted-foreground">
                        {percent}%
                      </span>
                    </span>
                  </div>

                  <p className="mt-2.5 border-l-2 border-brand-300 pl-2.5 text-xs leading-relaxed text-muted-foreground dark:border-brand-800">
                    {source.snippet}
                  </p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </aside>
  );
}
