"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type KeyboardEvent,
} from "react";
import { api, ApiError } from "@/lib/api";
import { tableToChart } from "@/lib/table-chart";
import { SUGGESTED_QUESTIONS, type ChatMessage } from "@/lib/types";
import Icon from "@/components/ui/Icon";
import ChartBlock from "./ChartBlock";
import EvidenceRail, { type EvidenceTurn } from "./EvidenceRail";
import MermaidDiagram from "./MermaidDiagram";
import SourceCitations from "./SourceCitations";

type Props = {
  selectedDocumentIds: string[];
  hasDocuments: boolean;
};

let messageCounter = 0;
const nextId = () => `msg-${++messageCounter}`;

export default function ChatPanel({ selectedDocumentIds, hasDocuments }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // The question currently open in the inline editor, plus its draft text.
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const editRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const stickToBottom = useRef(true);
  const copyTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Focus and size the inline editor when a question is opened for editing.
  useEffect(() => {
    if (!editingId) return;
    const el = editRef.current;
    if (!el) return;
    el.focus();
    el.setSelectionRange(el.value.length, el.value.length);
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [editingId]);

  // Clear a pending "Copied" reset if the panel unmounts first.
  useEffect(() => {
    return () => {
      if (copyTimer.current) clearTimeout(copyTimer.current);
    };
  }, []);

  // Follow new content, but stop fighting the reader once they scroll up.
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 96;
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages, pending]);

  // Grow the composer with its content instead of scrolling inside a fixed box.
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [question]);

  /**
   * Pick a chart for an answer: prefer what the model emitted, otherwise read one
   * out of a markdown table. llama3.1, the default model, ignores the chart
   * instruction and answers numeric questions with a table instead, so this
   * fallback is what makes charts appear without switching models.
   */
  function chartFor(message: ChatMessage) {
    if (message.chart) return message.chart;
    if (message.role !== "assistant" || message.streaming) return null;
    if (message.hasContext === false) return null;
    const inferred = tableToChart(message.content);
    return inferred
      ? { type: inferred.kind, title: inferred.title, data: inferred.data }
      : null;
  }

  const turns = useMemo<EvidenceTurn[]>(() => {
    const questions = messages.filter((message) => message.role === "user");
    return messages
      .filter((message) => message.role === "assistant")
      .map((answer, index) => ({
        id: answer.id,
        question: questions[index]?.content ?? "",
        sources: answer.sources,
      }));
  }, [messages]);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || pending) return;

    setError(null);
    setQuestion("");
    setPending(true);

    const userId = nextId();
    const answerId = nextId();
    stickToBottom.current = true;
    setActiveId(answerId);
    setMessages((current) => [
      ...current,
      { id: userId, role: "user", content: trimmed, sources: [] },
      { id: answerId, role: "assistant", content: "", sources: [], streaming: true },
    ]);

    // Tokens are appended as they arrive, so the answer is readable while the
    // model is still generating. The final response replaces this text.
    const appendToken = (chunk: string) => {
      setMessages((current) =>
        current.map((message) =>
          message.id === answerId
            ? { ...message, content: message.content + chunk }
            : message,
        ),
      );
    };

    try {
      const answer = await api.askStream(trimmed, selectedDocumentIds, {
        onToken: appendToken,
        onSources: ({ sources }) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === answerId ? { ...message, sources } : message,
            ),
          );
        },
      });

      setMessages((current) =>
        current.map((message) =>
          message.id === answerId
            ? {
                ...message,
                content: answer.answer,
                sources: answer.sources,
                hasContext: answer.has_context,
                model: answer.model,
                chart: answer.chart ?? null,
                diagram: answer.diagram ?? null,
                streaming: false,
              }
            : message,
        ),
      );
    } catch (caught) {
      const detail = caught instanceof ApiError ? caught.message : "Request failed";
      setError(detail);
      setMessages((current) =>
        current.map((message) =>
          message.id === answerId
            ? {
                ...message,
                content: `Sorry — ${detail}`,
                sources: [],
                hasContext: false,
                chart: null,
                diagram: null,
                streaming: false,
              }
            : message,
        ),
      );
    } finally {
      setPending(false);
    }
  }

  function startEdit(message: ChatMessage) {
    setEditingId(message.id);
    setDraft(message.content);
    // The editor replaces the bubble, so keep the view where it is.
    stickToBottom.current = true;
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft("");
  }

  function submitEdit(messageId: string) {
    const trimmed = draft.trim();
    if (!trimmed || pending) return;

    const original = messages.find((message) => message.id === messageId);
    if (!original || trimmed === original.content) {
      cancelEdit();
      return;
    }

    // Re-asking invalidates this turn and everything after it, so the later
    // answers can no longer be read as replies to the new question.
    const index = messages.findIndex((message) => message.id === messageId);
    setMessages(messages.slice(0, index));
    cancelEdit();
    void ask(trimmed);
  }

  function handleEditKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
    if (event.key === "Escape") {
      event.preventDefault();
      cancelEdit();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(question);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void ask(question);
    }
  }

  async function resetConversation() {
    setMessages([]);
    setActiveId(null);
    setError(null);
    cancelEdit();
    stickToBottom.current = true;
    try {
      await api.clearHistory();
    } catch {
      // A failed history reset should not block the local clear.
    }
  }

  async function copyAnswer(message: ChatMessage) {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopiedId(message.id);
      copyTimer.current = setTimeout(() => setCopiedId(null), 2000);
    } catch {
      // Clipboard access can be denied; silently ignore.
    }
  }

  const scopeLabel =
    selectedDocumentIds.length === 0
      ? "all documents"
      : `${selectedDocumentIds.length} selected document${selectedDocumentIds.length > 1 ? "s" : ""}`;

  return (
    <div className="flex min-h-0 min-w-0 flex-1 gap-4">
      <section className="card animate-fade-up flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-line px-5 py-3.5">
          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-700 dark:bg-brand-950/60 dark:text-brand-300">
            <Icon name="chat" className="size-4" />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold">Ask your documents</h2>
            <p className="truncate text-xs text-muted-foreground">
              Searching {scopeLabel} · answers use retrieved context only
            </p>
          </div>
          {messages.length > 0 && (
            <button
              type="button"
              className="btn-secondary btn-sm ml-auto shrink-0"
              onClick={resetConversation}
            >
              <Icon name="refresh" className="size-3.5" />
              New chat
            </button>
          )}
        </header>

        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="min-h-0 flex-1 space-y-6 overflow-y-auto px-5 py-6"
        >
          {messages.length === 0 && (
            <div className="animate-fade-up flex h-full flex-col items-center justify-center px-2 text-center">
              <span className="animate-float mb-5 grid size-14 place-items-center rounded-2xl bg-linear-to-br from-brand-500 to-accent-500 text-white shadow-lg shadow-brand-600/25">
                <Icon name="sparkles" className="size-6" strokeWidth={1.8} />
              </span>
              <h3 className="text-lg font-semibold">
                {hasDocuments
                  ? "What would you like to know?"
                  : "Upload a PDF to get started"}
              </h3>
              <p className="mt-1.5 max-w-sm text-sm leading-relaxed text-muted-foreground text-pretty">
                {hasDocuments
                  ? "Answers are drawn only from your documents, with the source page shown for every claim."
                  : "Once a document is indexed, ask a question and the pages that support the answer are cited alongside it."}
              </p>
              {hasDocuments && (
                <div className="stagger mt-7 flex flex-wrap justify-center gap-2">
                  {SUGGESTED_QUESTIONS.map((suggestion, index) => (
                    <button
                      key={suggestion}
                      type="button"
                      style={{ "--index": index } as CSSProperties}
                      className="chip-interactive animate-pop-in"
                      onClick={() => void ask(suggestion)}
                    >
                      <Icon name="search" className="size-3" />
                      {suggestion}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((message) => {
            const chart = chartFor(message);
            return (
              <article
                key={message.id}
                className={`flex flex-col gap-2 ${
                  message.role === "user"
                    ? "animate-slide-left items-end"
                    : "animate-fade-up"
                }`}
              >
                <div
                  className={`flex items-center gap-2 ${
                    message.role === "user" ? "flex-row-reverse" : ""
                  }`}
                >
                  <span
                    className={`grid size-6 shrink-0 place-items-center rounded-lg ${
                      message.role === "user"
                        ? "bg-muted text-muted-foreground"
                        : "bg-brand-600 text-white"
                    }`}
                    aria-hidden="true"
                  >
                    <Icon
                      name={message.role === "user" ? "user" : "sparkles"}
                      className="size-3.5"
                    />
                  </span>
                  <span className="text-[0.6875rem] font-semibold tracking-wide text-muted-foreground uppercase">
                    {message.role === "user" ? "You" : "Assistant"}
                  </span>
                  {message.role === "user" &&
                    !pending &&
                    (editingId === message.id ? null : (
                      <button
                        type="button"
                        onClick={() => startEdit(message)}
                        className="btn-secondary btn-sm ml-auto shrink-0 gap-1.5"
                        aria-label="Edit question"
                      >
                        <Icon name="pencil" className="size-3.5" />
                        Edit
                      </button>
                    ))}
                  {message.role === "assistant" && message.model && (
                    <span className="chip py-0.5">{message.model}</span>
                  )}
                  {message.role === "assistant" && !message.streaming && (
                    <button
                      type="button"
                      onClick={() => void copyAnswer(message)}
                      className={`btn-secondary btn-sm ml-auto shrink-0 gap-1.5 ${
                        copiedId === message.id
                          ? "border-emerald-300 bg-emerald-50 text-emerald-700 dark:border-emerald-700/60 dark:bg-emerald-950/50 dark:text-emerald-300"
                          : ""
                      }`}
                      aria-label="Copy answer"
                    >
                      <Icon
                        name={copiedId === message.id ? "check" : "copy"}
                        className="size-3.5"
                      />
                      {copiedId === message.id ? "Copied" : "Copy"}
                    </button>
                  )}
                </div>

                {message.role === "user" && editingId === message.id ? (
                  <form
                    onSubmit={(event) => {
                      event.preventDefault();
                      submitEdit(message.id);
                    }}
                    className="card animate-fade-up flex w-full max-w-3xl flex-col gap-2.5 p-3"
                  >
                    <label
                      htmlFor={`edit-${message.id}`}
                      className="text-[0.6875rem] font-semibold tracking-wide text-muted-foreground uppercase"
                    >
                      Edit question
                    </label>
                    <textarea
                      id={`edit-${message.id}`}
                      ref={editRef}
                      value={draft}
                      onChange={(event) => {
                        setDraft(event.target.value);
                        const el = event.target;
                        el.style.height = "auto";
                        el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
                      }}
                      onKeyDown={handleEditKeyDown}
                      rows={2}
                      maxLength={2000}
                      className="field resize-none text-sm"
                    />
                    <div className="flex items-center gap-2">
                      <button
                        type="submit"
                        disabled={!draft.trim() || pending}
                        className="btn-primary btn-sm"
                      >
                        <Icon name="send" className="size-3.5" />
                        Ask again
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        className="btn-secondary btn-sm"
                      >
                        Cancel
                      </button>
                      <span className="ml-auto text-[0.6875rem] text-muted-foreground">
                        Enter to send · Esc to cancel
                      </span>
                    </div>
                  </form>
                ) : (
                  <div
                    className={`max-w-3xl rounded-2xl px-4 py-3 text-sm whitespace-pre-wrap transition-shadow duration-300 ${
                      message.role === "user"
                        ? "self-end rounded-br-sm bg-brand-600 text-white shadow-md shadow-brand-600/20"
                        : "card"
                    }`}
                  >
                    {message.role === "assistant" && message.hasContext === false && (
                      <p className="mb-2.5 flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800/70 dark:bg-amber-950/40 dark:text-amber-200">
                        <Icon name="alert" className="mt-px size-3.5 shrink-0" />
                        No supporting context was found in the selected documents.
                      </p>
                    )}
                    <p className={message.streaming ? "answer caret" : "answer"}>
                      {message.content}
                    </p>
                    {message.role === "assistant" && !message.streaming && (
                      <>
                        {chart && <ChartBlock chart={chart} />}
                        {message.diagram && <MermaidDiagram source={message.diagram} />}
                      </>
                    )}
                    {message.role === "assistant" && (
                      <SourceCitations sources={message.sources} />
                    )}
                </div>
              )}
              </article>
            );
          })}

          {pending && !messages.some((message) => message.streaming) && (
            <div className="animate-fade-up flex items-center gap-2.5 text-sm text-muted-foreground">
              <span className="flex gap-1">
                {[0, 1, 2].map((dot) => (
                  <span
                    key={dot}
                    className="size-1.5 rounded-full bg-brand-500"
                    style={{
                      animation: `typing-dot 1.1s ease-in-out ${dot * 160}ms infinite`,
                    }}
                  />
                ))}
              </span>
              Searching your documents…
            </div>
          )}
        </div>

        <form
          onSubmit={handleSubmit}
          className="border-t border-line bg-muted/30 p-4"
        >
          {error && (
            <p
              role="alert"
              className="mb-3 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            >
              <Icon name="alert" className="mt-px size-3.5 shrink-0" />
              {error}
            </p>
          )}
          <div className="flex items-end gap-2">
            <textarea
              ref={textareaRef}
              rows={1}
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                hasDocuments ? "Ask anything about your documents…" : "Upload a PDF first"
              }
              disabled={!hasDocuments || pending}
              className="field max-h-40 flex-1 resize-none bg-card py-3"
            />
            <button
              type="submit"
              className="btn-primary shrink-0 py-3"
              disabled={!hasDocuments || pending || question.trim().length === 0}
            >
              <Icon
                name={pending ? "spinner" : "send"}
                className={`size-4 ${pending ? "animate-spin-slow" : ""}`}
              />
              {pending ? "Asking…" : "Ask"}
            </button>
          </div>
          <p className="mt-2.5 text-xs text-muted-foreground">
            Searching: {scopeLabel} · Enter to send, Shift+Enter for a new line
          </p>
        </form>
      </section>

      <EvidenceRail turns={turns} activeId={activeId} onSelect={setActiveId} />
    </div>
  );
}
