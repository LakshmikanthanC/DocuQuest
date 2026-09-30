"use client";

import { useRef, useState, type ChangeEvent, type CSSProperties, type DragEvent, type FormEvent } from "react";
import { api, ApiError } from "@/lib/api";
import type { DocumentStatus, UploadedDocument } from "@/lib/types";
import Icon from "@/components/ui/Icon";
import { cx } from "@/lib/cx";

type Props = {
  documents: UploadedDocument[];
  selectedIds: string[];
  open: boolean;
  collapsed: boolean;
  onSelectionChange: (ids: string[]) => void;
  onDocumentsChange: (documents: UploadedDocument[]) => void;
  onClose: () => void;
};

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

const STATUS_META: Record<
  DocumentStatus,
  { label: string; dot: string; text: string }
> = {
  ready: {
    label: "Indexed",
    dot: "bg-emerald-500",
    text: "text-emerald-700 dark:text-emerald-400",
  },
  processing: {
    label: "Indexing",
    dot: "bg-amber-500",
    text: "text-amber-700 dark:text-amber-400",
  },
  failed: {
    label: "Failed",
    dot: "bg-red-500",
    text: "text-red-700 dark:text-red-400",
  },
};

export default function DocumentSidebar({
  documents,
  selectedIds,
  open,
  collapsed,
  onSelectionChange,
  onDocumentsChange,
  onClose,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const readyCount = documents.filter((doc) => doc.status === "ready").length;
  const allSelected =
    documents.length > 0 && selectedIds.length === documents.length;

  function toggle(id: string) {
    onSelectionChange(
      selectedIds.includes(id)
        ? selectedIds.filter((value) => value !== id)
        : [...selectedIds, id],
    );
  }

  async function uploadFile(file: File) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are supported.");
      return;
    }

    setError(null);
    setBusy(true);
    try {
      const created = await api.uploadDocument(file);
      onDocumentsChange([created, ...documents]);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Upload failed");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const file = inputRef.current?.files?.[0];
    if (file) void uploadFile(file);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void uploadFile(file);
  }

  function handleDrop(event: DragEvent<HTMLFormElement>) {
    event.preventDefault();
    setDragging(false);
    const file = event.dataTransfer.files?.[0];
    if (file) void uploadFile(file);
  }

  async function remove(id: string) {
    const previous = documents;
    onDocumentsChange(documents.filter((doc) => doc.id !== id));
    onSelectionChange(selectedIds.filter((value) => value !== id));
    try {
      await api.deleteDocument(id);
    } catch (caught) {
      onDocumentsChange(previous);
      setError(caught instanceof ApiError ? caught.message : "Delete failed");
    }
  }

  return (
    <aside
      className={cx(
        "fixed inset-y-0 left-0 z-50 shrink-0 transition-[width,transform] duration-300 ease-out",
        "lg:static lg:z-auto lg:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
        collapsed ? "lg:w-0 lg:overflow-hidden" : "lg:w-72",
      )}
    >
      <section className="card flex h-full w-72 flex-col rounded-none border-y-0 border-l-0 lg:rounded-2xl lg:border-l">
        <header className="flex items-center gap-2 border-b border-line px-4 py-3.5">
          <Icon
            name="layers"
            className="size-4 shrink-0 text-brand-600 dark:text-brand-400"
          />
          <h2 className="text-sm font-semibold">Documents</h2>
          {documents.length > 0 && (
            <span className="chip ml-auto py-0.5 tabular-nums">
              {readyCount}/{documents.length}
            </span>
          )}
          <button
            type="button"
            onClick={onClose}
            className="icon-btn -mr-1.5 size-8 lg:hidden"
            aria-label="Close documents"
          >
            <Icon name="close" className="size-4" />
          </button>
        </header>

        <form
          onSubmit={handleSubmit}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className="p-3"
        >
          <div
            className={cx(
              "rounded-xl border-2 border-dashed px-4 py-5 text-center transition-all duration-300",
              dragging
                ? "scale-[1.02] border-brand-500 bg-brand-50 shadow-md shadow-brand-500/10 dark:bg-brand-950/40"
                : "border-line-strong hover:border-brand-400 hover:bg-brand-50/50 dark:hover:bg-brand-950/20",
            )}
          >
            <span
              className={cx(
                "mx-auto mb-2 grid size-9 place-items-center rounded-full transition-all duration-300",
                dragging
                  ? "animate-breathe -translate-y-0.5 bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300"
                  : "bg-muted text-muted-foreground",
              )}
            >
              <Icon name={dragging ? "upload" : "file"} className="size-4.5" />
            </span>
            <p className="text-sm font-medium">
              {dragging ? "Release to upload" : "Drop a PDF here"}
            </p>
            <button
              type="button"
              className="btn-secondary btn-sm mt-2.5"
              disabled={busy}
              onClick={() => inputRef.current?.click()}
            >
              {busy ? (
                <>
                  <Icon name="spinner" className="size-3.5 animate-spin-slow" />
                  Uploading…
                </>
              ) : (
                "Choose file"
              )}
            </button>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf,.pdf"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {error && (
            <p
              role="alert"
              className="mt-3 flex items-start gap-2 rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300"
            >
              <Icon name="alert" className="mt-px size-3.5 shrink-0" />
              {error}
            </p>
          )}
        </form>

        {documents.length > 0 && (
          <div className="flex items-center justify-between border-y border-line px-4 py-2">
            <span className="text-[0.6875rem] font-medium tracking-wide text-muted-foreground uppercase">
              Ask about
            </span>
            <button
              type="button"
              className="text-xs font-semibold text-brand-700 transition-colors hover:text-brand-600 dark:text-brand-300"
              onClick={() =>
                onSelectionChange(allSelected ? [] : documents.map((doc) => doc.id))
              }
            >
              {allSelected ? "Clear all" : "Select all"}
            </button>
          </div>
        )}

        <ul className="stagger min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
          {documents.map((doc, index) => {
            const selected = selectedIds.includes(doc.id);
            const status = STATUS_META[doc.status];
            return (
              <li
                key={doc.id}
                style={{ "--index": index } as CSSProperties}
                className="animate-slide-left"
              >
                <div
                  className={cx(
                    "group flex items-start gap-2.5 rounded-xl p-2.5 transition-all duration-200",
                    selected
                      ? "bg-brand-50 ring-1 ring-brand-200 dark:bg-brand-950/50 dark:ring-brand-800"
                      : "hover:bg-muted",
                  )}
                >
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={() => toggle(doc.id)}
                    className="mt-1 size-4 shrink-0 accent-brand-600"
                    aria-label={`Use ${doc.filename} as context`}
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium" title={doc.filename}>
                      {doc.filename}
                    </p>
                    <p className="mt-0.5 text-xs text-muted-foreground tabular-nums">
                      {doc.page_count} pages · {doc.chunk_count} chunks ·{" "}
                      {formatBytes(doc.size_bytes)}
                    </p>
                    <p
                      className={cx(
                        "mt-1 flex items-center gap-1.5 text-xs font-medium",
                        status.text,
                      )}
                    >
                      {doc.status === "processing" ? (
                        <Icon
                          name="spinner"
                          className="size-3 animate-spin-slow"
                        />
                      ) : (
                        <span
                          className={cx("size-1.5 rounded-full", status.dot)}
                        />
                      )}
                      {status.label}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => void remove(doc.id)}
                    className="btn-danger -mt-0.5 -mr-0.5 size-7 shrink-0 rounded-lg opacity-0 transition-opacity focus-visible:opacity-100 group-hover:opacity-100"
                    aria-label={`Delete ${doc.filename}`}
                  >
                    <Icon name="trash" className="size-3.5" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>

        {documents.length === 0 && (
          <p className="px-4 pb-4 text-center text-xs leading-relaxed text-muted-foreground">
            Your uploaded files appear here, and every one of them is searched
            by default.
          </p>
        )}
      </section>
    </aside>
  );
}
