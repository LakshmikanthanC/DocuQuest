"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api, clearToken, getToken } from "@/lib/api";
import type { Health, UploadedDocument, User } from "@/lib/types";
import ThemeToggle from "@/components/theme/ThemeToggle";
import Icon from "@/components/ui/Icon";
import Logo from "@/components/ui/Logo";
import AuthView from "./AuthView";
import ChatPanel from "./ChatPanel";
import DocumentSidebar from "./DocumentSidebar";

type Status = "checking" | "authenticated" | "anonymous";

function ShellSkeleton() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-card px-4">
        <div className="animate-shimmer size-8 rounded-lg" />
        <div className="animate-shimmer h-3.5 w-28 rounded" />
        <div className="animate-shimmer ml-auto h-8 w-40 rounded-lg" />
      </header>
      <main className="flex min-h-0 flex-1 gap-4 p-4 sm:p-5">
        <div className="animate-shimmer hidden w-72 shrink-0 rounded-2xl lg:block" />
        <div className="animate-shimmer min-w-0 flex-1 rounded-2xl" />
      </main>
    </div>
  );
}

export default function RagAssistant() {
  const [authState, setAuthState] = useState<Status>("checking");
  const [user, setUser] = useState<User | null>(null);
  const [documents, setDocuments] = useState<UploadedDocument[]>([]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      const result = await api.listDocuments();
      setDocuments(result.documents);
    } catch {
      // A failed document fetch should not block the chat UI.
    }
  }, []);

  useEffect(() => {
    let active = true;

    const boot = async () => {
      const result = await api.health().catch(() => null);
      if (active && result) setHealth(result);

      if (!getToken()) {
        if (active) setAuthState("anonymous");
        return;
      }

      try {
        const currentUser = await api.me();
        if (!active) return;
        setUser(currentUser);
        setAuthState("authenticated");
        void loadDocuments();
      } catch {
        if (!active) return;
        clearToken();
        setAuthState("anonymous");
      }
    };

    void boot();
    return () => {
      active = false;
    };
  }, [loadDocuments]);

  // Indexing happens in the background on upload, so poll until nothing is pending.
  useEffect(() => {
    if (authState !== "authenticated") return;
    if (!documents.some((doc) => doc.status === "processing")) return;

    const timer = setInterval(() => void loadDocuments(), 2500);
    return () => clearInterval(timer);
  }, [authState, documents, loadDocuments]);

  // Escape closes the document drawer on small screens.
  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  async function handleAuthenticated() {
    setAuthState("authenticated");
    setUser(await api.me().catch(() => null));
    void loadDocuments();
  }

  function handleSignOut() {
    clearToken();
    setUser(null);
    setDocuments([]);
    setSelectedIds([]);
    setDrawerOpen(false);
    setAuthState("anonymous");
  }

  if (authState === "checking") return <ShellSkeleton />;
  if (authState === "anonymous") return <AuthView onAuthenticated={handleAuthenticated} />;

  const readyCount = documents.filter((doc) => doc.status === "ready").length;
  const hasDocuments = readyCount > 0;
  const llmOnline = health?.llm.includes("online") ?? false;

  return (
    <div className="flex h-dvh flex-col overflow-hidden">
      <header className="z-30 flex h-14 shrink-0 items-center gap-2 border-b border-line bg-card/85 px-3 backdrop-blur-md sm:gap-3 sm:px-4">
        <button
          type="button"
          className="icon-btn lg:hidden"
          onClick={() => setDrawerOpen(true)}
          aria-label="Open documents"
          aria-expanded={drawerOpen}
        >
          <Icon name="panelLeft" className="size-5" />
        </button>
        <button
          type="button"
          className="icon-btn hidden lg:inline-flex"
          onClick={() => setSidebarCollapsed((value) => !value)}
          aria-label={sidebarCollapsed ? "Show documents" : "Hide documents"}
          aria-pressed={!sidebarCollapsed}
        >
          <Icon name="panelLeft" className="size-5" />
        </button>

        <Link href="/" aria-label="RAG Assistant home" className="shrink-0">
          <Logo className="hidden sm:inline-flex" />
          <Logo showWordmark={false} className="sm:hidden" />
        </Link>

        <span className="hidden h-5 w-px bg-line md:block" aria-hidden="true" />

        <div className="hidden min-w-0 items-center gap-2 md:flex">
          <Icon name="layers" className="size-3.5 shrink-0 text-muted-foreground" />
          <p className="truncate text-xs text-muted-foreground tabular-nums">
            {documents.length === 0
              ? "No documents"
              : `${readyCount} of ${documents.length} indexed`}
          </p>
        </div>

        <div className="ml-auto flex items-center gap-1.5 sm:gap-2.5">
          {health && (
            <span
              className="chip hidden sm:inline-flex"
              title={`Vector store: ${health.vector_store} · Embeddings: ${health.embedding_model}`}
            >
              <span className="relative flex size-1.5" aria-hidden="true">
                {llmOnline && (
                  <span className="animate-ping absolute inline-flex size-full rounded-full bg-emerald-400 opacity-75" />
                )}
                <span
                  className={`relative inline-flex size-1.5 rounded-full ${
                    llmOnline ? "bg-emerald-500" : "bg-amber-500"
                  }`}
                />
              </span>
              {health.llm}
            </span>
          )}

          {user && (
            <span className="hidden max-w-40 truncate text-xs text-muted-foreground lg:inline">
              {user.email}
            </span>
          )}

          <ThemeToggle />

          <button type="button" className="icon-btn" onClick={handleSignOut} aria-label="Sign out">
            <Icon name="logout" className="size-4.5" />
          </button>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-[100rem] min-h-0 flex-1 gap-4 p-3 sm:p-4">
        <DocumentSidebar
          documents={documents}
          selectedIds={selectedIds}
          open={drawerOpen}
          collapsed={sidebarCollapsed}
          onSelectionChange={setSelectedIds}
          onDocumentsChange={setDocuments}
          onClose={() => setDrawerOpen(false)}
        />

        <ChatPanel selectedDocumentIds={selectedIds} hasDocuments={hasDocuments} />
      </main>

      {drawerOpen && (
        <button
          type="button"
          onClick={() => setDrawerOpen(false)}
          aria-label="Close documents"
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm lg:hidden"
        />
      )}

      {!llmOnline && health && (
        <p className="flex shrink-0 flex-wrap items-center justify-center gap-1.5 border-t border-amber-300 bg-amber-50 px-4 py-2 text-center text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
          <Icon name="alert" className="size-3.5 shrink-0" />
          Ollama is not reachable at {String(health.details.ollama_url ?? "")}. Start it with
          <code className="rounded bg-amber-100 px-1 py-0.5 font-mono dark:bg-amber-900/60">
            ollama serve
          </code>
          and pull
          <code className="rounded bg-amber-100 px-1 py-0.5 font-mono dark:bg-amber-900/60">
            {health.llm.split(" ")[0]}
          </code>
          .
        </p>
      )}
    </div>
  );
}
