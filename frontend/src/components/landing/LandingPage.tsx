import Link from "next/link";
import type { ReactNode } from "react";
import Icon from "@/components/ui/Icon";
import Logo from "@/components/ui/Logo";
import HeroMockup from "./HeroMockup";
import SiteHeader from "./SiteHeader";
import { FAQS, FEATURES, STATS, STEPS } from "./content";

function SectionHeading({
  eyebrow,
  title,
  lede,
  align = "center",
}: {
  eyebrow: string;
  title: ReactNode;
  lede?: ReactNode;
  align?: "center" | "left";
}) {
  return (
    <div className={align === "center" ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      <p className="text-xs font-semibold tracking-[0.14em] text-brand-700 uppercase dark:text-brand-300">
        {eyebrow}
      </p>
      <h2 className="mt-3 font-display text-3xl leading-[1.15] tracking-tight text-balance sm:text-4xl">
        {title}
      </h2>
      {lede && (
        <p className="mt-4 text-base leading-relaxed text-muted-foreground text-pretty">
          {lede}
        </p>
      )}
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col">
      <SiteHeader />

      <main className="flex-1">
        {/* ---------------------------------------------------------------- Hero */}
        <section className="aurora relative overflow-hidden">
          <div aria-hidden="true" className="absolute inset-0 -z-10 bg-grid" />
          <div className="mx-auto w-full max-w-6xl px-5 pt-16 pb-20 sm:px-6 sm:pt-24">
            <div className="animate-fade-up mx-auto max-w-3xl text-center">
              <span className="chip animate-pop-in border-brand-300/70 bg-brand-50 text-brand-800 dark:border-brand-800 dark:bg-brand-950/50 dark:text-brand-200">
                <Icon name="zap" className="size-3" />
                Retrieval-augmented · runs entirely on your machine
              </span>

              <h1 className="mt-6 font-display text-4xl leading-[1.08] tracking-tight text-balance sm:text-6xl">
                Ask your PDFs anything,
                <br className="hidden sm:block" /> get answers you can{" "}
                <span className="gradient-text italic">check</span>
              </h1>

              <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground text-pretty">
                RAG Assistant searches your documents by meaning, answers only from the
                passages it retrieves, and cites the exact page behind every
                claim. No guessing, no black box.
              </p>

              <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Link href="/workspace" className="btn-primary w-full px-6 py-3 sm:w-auto">
                  Open the workspace
                  <Icon name="arrowRight" className="size-4" />
                </Link>
                <a href="#how-it-works" className="btn-secondary w-full px-6 py-3 sm:w-auto">
                  See how it works
                </a>
              </div>
            </div>

            <div className="animate-fade-up mt-16 [animation-delay:200ms]">
              <HeroMockup />
            </div>
          </div>
        </section>

        {/* -------------------------------------------------------------- Stats */}
        <section className="border-y border-line bg-muted/40">
          <div className="mx-auto grid w-full max-w-6xl gap-8 px-5 py-10 sm:grid-cols-3 sm:px-6">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center sm:text-left">
                <p className="font-display text-2xl tracking-tight text-brand-700 dark:text-brand-300">
                  {stat.value}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ------------------------------------------------------------ Features */}
        <section id="features" className="scroll-mt-20 py-20 sm:py-28">
          <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
            <SectionHeading
              eyebrow="Features"
              title="Everything you need to trust a machine-generated answer"
              lede="The retrieval pipeline, the guardrails, and the citations are all part of the product — not an afterthought."
            />

            <div className="stagger mt-14 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature, index) => (
                <div
                  key={feature.title}
                  style={{ "--index": index } as React.CSSProperties}
                  className="card card-lift animate-fade-up p-6"
                >
                  <span className="inline-grid size-10 place-items-center rounded-xl bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
                    <Icon name={feature.icon} className="size-5" />
                  </span>
                  <h3 className="mt-4 text-base font-semibold">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {feature.body}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* -------------------------------------------------------- How it works */}
        <section
          id="how-it-works"
          className="scroll-mt-20 border-y border-line bg-muted/40 py-20 sm:py-28"
        >
          <div className="mx-auto w-full max-w-6xl px-5 sm:px-6">
            <SectionHeading
              eyebrow="How it works"
              title="Three steps from PDF to cited answer"
            />

            <ol className="mt-14 grid gap-6 lg:grid-cols-3">
              {STEPS.map((step, index) => (
                <li key={step.title} className="relative">
                  <span className="font-display text-5xl leading-none text-brand-600/25 dark:text-brand-400/25">
                    {String(index + 1).padStart(2, "0")}
                  </span>
                  <h3 className="mt-3 text-lg font-semibold">{step.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                    {step.body}
                  </p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* --------------------------------------------------------- Verification */}
        <section id="verification" className="scroll-mt-20 py-20 sm:py-28">
          <div className="mx-auto grid w-full max-w-6xl items-center gap-14 px-5 sm:px-6 lg:grid-cols-2">
            <div>
              <p className="text-xs font-semibold tracking-[0.14em] text-brand-700 uppercase dark:text-brand-300">
                Verification
              </p>
              <h2 className="mt-3 font-display text-3xl leading-[1.15] tracking-tight text-balance sm:text-4xl">
                When the model does not know, it says so
              </h2>
              <p className="mt-4 text-base leading-relaxed text-muted-foreground">
                A confident wrong answer is worse than no answer. If the
                retrieved context is thin, the model is expected to decline —
                and the interface flags that reply so you never mistake a
                refusal for a result.
              </p>

              <ul className="mt-8 space-y-4">
                {[
                  {
                    icon: "target" as const,
                    title: "Context-only prompting",
                    body: "The retrieved passages are the only permitted source of truth for the answer.",
                  },
                  {
                    icon: "shield" as const,
                    title: "Refusal detection",
                    body: "A decline is recognised server-side and surfaced as a warning, not buried.",
                  },
                  {
                    icon: "database" as const,
                    title: "No retrieval, no call",
                    body: "When similarity search returns nothing, the language model is never invoked.",
                  },
                ].map((item) => (
                  <li key={item.title} className="flex gap-3.5">
                    <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg border border-line bg-card text-brand-700 dark:text-brand-300">
                      <Icon name={item.icon} className="size-4" />
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{item.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-muted-foreground">
                        {item.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            {/* Citation card */}
            <div className="animate-float">
              <div className="card shadow-pop">
                <div className="border-b border-line px-5 py-3.5">
                  <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                    Sources
                  </p>
                </div>
                <div className="space-y-3 p-5">
                  <div className="rounded-xl border border-line bg-muted/50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="chip border-brand-300/70 bg-brand-50 text-brand-800 dark:border-brand-800 dark:bg-brand-950/50 dark:text-brand-200">
                        <Icon name="file" className="size-3" />
                        quarterly-report.pdf
                      </span>
                      <span className="chip">Page 12</span>
                      <span className="ml-auto flex items-center gap-1.5 text-[0.6875rem] text-muted-foreground">
                        <span className="h-1 w-10 overflow-hidden rounded-full bg-line">
                          <span className="block h-full w-[82%] rounded-full bg-brand-500" />
                        </span>
                        <span className="tabular-nums">82%</span>
                      </span>
                    </div>
                    <blockquote className="mt-3 flex gap-2.5 text-sm leading-relaxed text-muted-foreground">
                      <Icon
                        name="quote"
                        className="mt-0.5 size-4 shrink-0 text-brand-500"
                      />
                      <p>
                        Operating expenses rose 4% year over year while revenue
                        grew 11%, driven primarily by the infrastructure
                        consolidation completed in the second quarter…
                      </p>
                    </blockquote>
                  </div>

                  <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-200">
                    <span className="inline-flex items-center gap-2 font-medium">
                      <Icon name="alert" className="size-4 shrink-0" />
                      No supporting context was found in the selected documents.
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ----------------------------------------------------------------- FAQ */}
        <section id="faq" className="scroll-mt-20 border-t border-line py-20 sm:py-28">
          <div className="mx-auto w-full max-w-3xl px-5 sm:px-6">
            <SectionHeading eyebrow="FAQ" title="Questions worth asking" />

            <div className="mt-12 divide-y divide-line overflow-hidden rounded-2xl border border-line bg-card">
              {FAQS.map((faq) => (
                <details key={faq.q} className="group">
                  <summary className="flex cursor-pointer list-none items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium transition-colors hover:bg-muted/60 sm:px-6 sm:text-base">
                    {faq.q}
                    <Icon
                      name="chevronDown"
                      className="size-4 shrink-0 text-muted-foreground transition-transform duration-300 group-open:rotate-180"
                    />
                  </summary>
                  <p className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground sm:px-6">
                    {faq.a}
                  </p>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ----------------------------------------------------------------- CTA */}
        <section className="px-5 pb-20 sm:px-6 sm:pb-28">
          <div className="aurora mx-auto w-full max-w-6xl overflow-hidden rounded-3xl border border-line bg-card px-6 py-14 text-center shadow-pop sm:px-12">
            <h2 className="font-display text-3xl leading-tight tracking-tight text-balance sm:text-4xl">
              Point it at your documents
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-base text-muted-foreground text-pretty">
              Upload a PDF, ask a question, and see the page your answer came
              from.
            </p>
            <Link href="/workspace" className="btn-primary mt-8 px-6 py-3">
              Open the workspace
              <Icon name="arrowRight" className="size-4" />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex w-full max-w-6xl flex-col items-center justify-between gap-6 px-5 py-10 sm:flex-row sm:px-6">
          <div className="flex items-center gap-3">
            <Logo />
            <p className="text-sm text-muted-foreground">
              Answers you can check.
            </p>
          </div>
          <nav aria-label="Footer" className="flex flex-wrap items-center gap-x-6 gap-y-2">
            {[
              { href: "#features", label: "Features" },
              { href: "#how-it-works", label: "How it works" },
              { href: "#verification", label: "Verification" },
              { href: "#faq", label: "FAQ" },
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {link.label}
              </a>
            ))}
            <Link
              href="/workspace"
              className="text-sm font-medium text-brand-700 transition-colors hover:text-brand-600 dark:text-brand-300"
            >
              Sign in
            </Link>
          </nav>
        </div>
        <div className="border-t border-line">
          <p className="mx-auto w-full max-w-6xl px-5 py-5 text-center text-xs text-muted-foreground sm:px-6">
            Next.js · FastAPI · LangChain · ChromaDB · Ollama. MIT licensed.
          </p>
        </div>
      </footer>
    </div>
  );
}
