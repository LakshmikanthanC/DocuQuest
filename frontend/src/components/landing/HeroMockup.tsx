import Icon from "@/components/ui/Icon";

const DOCS = [
  { name: "quarterly-report.pdf", meta: "48 pages · 312 chunks", state: "ready" },
  { name: "field-notes-2024.pdf", meta: "17 pages · 96 chunks", state: "processing" },
];

const SOURCES = [
  { name: "quarterly-report.pdf", page: 12, score: 82 },
  { name: "field-notes-2024.pdf", page: 4, score: 71 },
  { name: "quarterly-report.pdf", page: 27, score: 58 },
];

/**
 * Purely decorative snapshot of the workspace, drawn with divs so the page
 * needs no image assets and the mockup always matches the real palette.
 */
export default function HeroMockup() {
  return (
    <div className="relative">
      <div
        aria-hidden="true"
        className="absolute -inset-x-8 -top-6 bottom-0 -z-10 rounded-[2.5rem] bg-linear-to-b from-brand-200/40 to-transparent blur-2xl dark:from-brand-900/30"
      />

      <div className="overflow-hidden rounded-2xl border border-line bg-card shadow-pop">
        {/* Window chrome */}
        <div className="flex items-center gap-3 border-b border-line bg-muted/60 px-4 py-3">
          <div className="flex gap-1.5">
            <span className="size-2.5 rounded-full bg-red-400/70" />
            <span className="size-2.5 rounded-full bg-amber-400/70" />
            <span className="size-2.5 rounded-full bg-emerald-400/70" />
          </div>
          <div className="mx-auto flex items-center gap-1.5 rounded-md border border-line bg-card px-2.5 py-1 text-[0.6875rem] text-muted-foreground">
            <Icon name="lock" className="size-3" />
            localhost:3000/workspace
          </div>
        </div>

        <div className="grid text-left sm:grid-cols-[11rem_1fr] xl:grid-cols-[12rem_1fr_13rem]">
          {/* Documents rail */}
          <div className="hidden flex-col gap-3 border-r border-line bg-muted/40 p-3 sm:flex">
            <p className="text-[0.6875rem] font-semibold tracking-wide text-muted-foreground uppercase">
              Documents
            </p>
            <div className="rounded-lg border border-dashed border-line-strong px-2 py-3 text-center">
              <Icon
                name="upload"
                className="mx-auto size-4 text-muted-foreground/70"
              />
              <p className="mt-1 text-[0.6875rem] text-muted-foreground">
                Drop a PDF
              </p>
            </div>
            {DOCS.map((doc, index) => (
              <div
                key={doc.name}
                className={
                  "rounded-lg border p-2 transition-colors " +
                  (index === 0
                    ? "border-brand-300/60 bg-brand-50 dark:border-brand-800/60 dark:bg-brand-950/40"
                    : "border-line bg-card")
                }
              >
                <div className="flex items-center gap-1.5">
                  <span
                    className={
                      "size-1.5 rounded-full " +
                      (doc.state === "ready" ? "bg-emerald-500" : "bg-amber-500")
                    }
                  />
                  <p className="truncate text-[0.6875rem] font-medium">
                    {doc.name}
                  </p>
                </div>
                <p className="mt-0.5 truncate text-[0.625rem] text-muted-foreground">
                  {doc.meta}
                </p>
              </div>
            ))}
          </div>

          {/* Conversation */}
          <div className="flex flex-col gap-3 p-4 sm:p-5">
            <div className="flex justify-end">
              <p className="max-w-[85%] rounded-xl rounded-br-sm bg-brand-600 px-3 py-2 text-xs text-white">
                What drove the increase in operating margin?
              </p>
            </div>

            <div className="rounded-xl border border-line bg-background p-3.5">
              <p className="text-xs leading-relaxed text-foreground/90">
                Margin expanded mainly on cost discipline rather than pricing.
                Operating expenses grew 4% against 11% revenue growth, led by the
                infrastructure consolidation completed in Q2.
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5 border-t border-line pt-3">
                {SOURCES.map((source) => (
                  <span key={`${source.name}-${source.page}`} className="chip">
                    <Icon name="file" className="size-3" />
                    <span className="max-w-24 truncate">{source.name}</span>
                    <span className="text-brand-700 dark:text-brand-300">
                      p.{source.page}
                    </span>
                  </span>
                ))}
              </div>
            </div>

            <div className="mt-auto flex items-center gap-2 rounded-xl border border-line bg-card px-3 py-2.5">
              <p className="flex-1 text-xs text-muted-foreground/70">
                Ask anything about your documents…
              </p>
              <span className="grid size-7 place-items-center rounded-lg bg-brand-600 text-white">
                <Icon name="send" className="size-3.5" />
              </span>
            </div>
          </div>

          {/* Evidence rail */}
          <div className="hidden flex-col gap-2.5 border-l border-line bg-muted/40 p-3 xl:flex">
            <p className="text-[0.6875rem] font-semibold tracking-wide text-muted-foreground uppercase">
              Evidence
            </p>
            {SOURCES.map((source) => (
              <div
                key={`rail-${source.name}-${source.page}`}
                className="rounded-lg border border-line bg-card p-2"
              >
                <div className="flex items-center gap-1.5">
                  <Icon
                    name="bookmark"
                    className="size-3 shrink-0 text-brand-600 dark:text-brand-400"
                  />
                  <span className="truncate text-[0.6875rem] font-medium">
                    {source.name}
                  </span>
                </div>
                <p className="mt-1 text-[0.625rem] text-muted-foreground">
                  Page {source.page}
                </p>
                <div className="mt-1.5 flex items-center gap-1.5">
                  <span className="h-1 flex-1 overflow-hidden rounded-full bg-line">
                    <span
                      className="block h-full rounded-full bg-brand-500"
                      style={{ width: `${source.score}%` }}
                    />
                  </span>
                  <span className="text-[0.625rem] tabular-nums text-muted-foreground">
                    {source.score}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
