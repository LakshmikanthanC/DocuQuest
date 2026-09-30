"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { api, ApiError, setToken } from "@/lib/api";
import type { TokenResponse } from "@/lib/types";
import ThemeToggle from "@/components/theme/ThemeToggle";
import Icon, { type IconName } from "@/components/ui/Icon";
import Logo from "@/components/ui/Logo";

type Mode = "login" | "register";

const PROOF_POINTS: { icon: IconName; title: string; body: string }[] = [
  {
    icon: "quote",
    title: "Cited by default",
    body: "Every answer links back to the filename, page, and snippet behind it.",
  },
  {
    icon: "shield",
    title: "Refuses rather than guesses",
    body: "Thin context produces an explicit “not found”, flagged in the interface.",
  },
  {
    icon: "lock",
    title: "Private per account",
    body: "Vectors are tagged by owner, so no query crosses accounts.",
  },
];

export default function AuthView({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isRegister = mode === "register";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const result: TokenResponse = isRegister
        ? await api.register(email, password, fullName)
        : await api.login(email, password);
      setToken(result.access_token);
      onAuthenticated();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="aurora relative flex min-h-dvh flex-1 items-center justify-center p-5 sm:p-8">
      <div
        aria-hidden="true"
        className="absolute inset-0 -z-10 bg-grid opacity-60"
      />

      <div className="absolute top-5 right-5 z-10">
        <ThemeToggle />
      </div>

      <div className="animate-pop-in grid w-full max-w-4xl overflow-hidden rounded-3xl border border-line bg-card shadow-pop md:grid-cols-2">
        {/* Brand panel */}
        <aside className="hidden flex-col justify-between border-r border-line bg-muted/50 p-9 md:flex">
          <Link href="/" aria-label="RAG Assistant home" className="w-fit">
            <Logo />
          </Link>

          <div>
            <h2 className="font-display text-3xl leading-[1.15] tracking-tight text-balance">
              Every answer, backed by a page you can open
            </h2>
            <ul className="mt-8 space-y-5">
              {PROOF_POINTS.map((point) => (
                <li key={point.title} className="flex gap-3">
                  <span className="mt-0.5 grid size-8 shrink-0 place-items-center rounded-lg bg-card text-brand-700 shadow-sm dark:text-brand-300">
                    <Icon name={point.icon} className="size-4" />
                  </span>
                  <div>
                    <p className="text-sm font-semibold">{point.title}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                      {point.body}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-xs text-muted-foreground">
            Runs locally with Ollama. Your documents stay on your machine.
          </p>
        </aside>

        {/* Form */}
        <div className="p-7 sm:p-10">
          <div className="mb-7">
            <Link href="/" aria-label="RAG Assistant home" className="mb-6 inline-flex md:hidden">
              <Logo />
            </Link>
            <h1 className="font-display text-2xl tracking-tight sm:text-3xl">
              {isRegister ? "Create your account" : "Welcome back"}
            </h1>
            <p className="mt-1.5 text-sm text-muted-foreground">
              {isRegister
                ? "Start asking questions in your own documents."
                : "Sign in to ask your documents anything."}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegister && (
              <div>
                <label htmlFor="name" className="label">
                  Full name
                </label>
                <input
                  id="name"
                  className="field"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Ada Lovelace"
                  autoComplete="name"
                />
              </div>
            )}

            <div>
              <label htmlFor="email" className="label">
                Email
              </label>
              <input
                id="email"
                type="email"
                required
                className="field"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label htmlFor="password" className="label">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                minLength={8}
                className="field"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 8 characters"
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
            </div>

            {error && (
              <p
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
              >
                <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
                {error}
              </p>
            )}

            <button type="submit" className="btn-primary w-full py-3" disabled={submitting}>
              {submitting ? (
                <>
                  <Icon name="spinner" className="size-4 animate-spin-slow" />
                  {isRegister ? "Creating account…" : "Signing in…"}
                </>
              ) : isRegister ? (
                "Create account"
              ) : (
                "Sign in"
              )}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {isRegister ? "Already have an account?" : "New here?"}{" "}
            <button
              type="button"
              className="font-semibold text-brand-700 transition-colors hover:text-brand-600 dark:text-brand-300"
              onClick={() => {
                setMode(isRegister ? "login" : "register");
                setError(null);
              }}
            >
              {isRegister ? "Sign in" : "Create an account"}
            </button>
          </p>

          <p className="mt-6 text-center text-xs text-muted-foreground md:hidden">
            <Link href="/" className="hover:text-foreground">
              ← Back to home
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
