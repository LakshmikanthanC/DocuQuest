"use client";

import { useEffect, useRef, useState } from "react";

import Icon from "@/components/ui/Icon";

/**
 * Renders a mermaid diagram, loading the library only when one is present.
 *
 * Mermaid pulls in a large dependency and is not needed by most answers, so it
 * is imported dynamically. Anything that goes wrong (missing library, invalid
 * syntax from a small model) degrades to the source in a <pre> rather than
 * breaking the answer.
 */

type State = "idle" | "loading" | "ready" | "error";

export default function MermaidDiagram({ source }: { source: string }) {
  const host = useRef<HTMLDivElement>(null);
  // Starts as "loading" so the placeholder shows on first paint; a new source
  // resets the outcome via the key React uses to remount this component.
  const [outcome, setOutcome] = useState<{ svg: string } | { error: true } | null>(null);
  const [open, setOpen] = useState(false);
  const state: State = outcome === null ? "loading" : "error" in outcome ? "error" : "ready";

  useEffect(() => {
    let cancelled = false;

    // Mermaid mutates the DOM it renders into, so each render gets a throwaway
    // container and only the resulting SVG is copied across.
    import("mermaid")
      .then(async ({ default: mermaid }) => {
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "neutral",
          fontFamily: "inherit",
        });
        const { svg: rendered } = await mermaid.render(
          `mermaid-${Math.random().toString(36).slice(2)}`,
          source,
        );
        if (!cancelled) setOutcome({ svg: rendered });
      })
      .catch(() => {
        if (!cancelled) setOutcome({ error: true });
      });

    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <figure className="card mt-3 overflow-hidden p-4 text-left">
      <figcaption className="mb-3 flex items-center gap-2">
        <Icon name="layers" className="size-3.5 text-brand-600" />
        <span className="text-xs font-semibold">Diagram</span>
        <span className="chip ml-auto py-0.5 text-[0.625rem]">mermaid</span>
        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          className="text-muted-foreground transition-colors hover:text-foreground"
          aria-label={open ? "Hide diagram source" : "Show diagram source"}
          aria-expanded={open}
        >
          <Icon name="code" className="size-3.5" />
        </button>
      </figcaption>

      {state === "loading" && (
        <div className="flex items-center gap-2 py-6 text-xs text-muted-foreground">
          <Icon name="spinner" className="size-3.5 animate-spin" />
          Rendering diagram…
        </div>
      )}

      {state === "error" && (
        <p className="mb-2 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-200">
          <Icon name="alert" className="mt-px size-3.5 shrink-0" />
          This diagram could not be rendered. The source is shown below.
        </p>
      )}

      {state === "ready" && !open && outcome && "svg" in outcome && (
        <div
          ref={host}
          className="flex justify-center overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto"
          // The markup comes from mermaid itself, rendered with
          // securityLevel "strict" from validated model output.
          dangerouslySetInnerHTML={{ __html: outcome.svg }}
        />
      )}

      {open && (
        <pre className="overflow-x-auto rounded-lg bg-muted p-3 text-[0.6875rem] leading-relaxed">
          <code>{source}</code>
        </pre>
      )}
    </figure>
  );
}
