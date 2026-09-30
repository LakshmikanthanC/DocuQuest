import type {
  Chart,
  ChatAnswer,
  DocumentList,
  Health,
  Source,
  TokenResponse,
  UploadedDocument,
  User,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000/api";

const TOKEN_KEY = "rag.token";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ---------------------------------------------------------------------------
// Token storage
// ---------------------------------------------------------------------------
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
}

// ---------------------------------------------------------------------------
// Request helper
// ---------------------------------------------------------------------------
async function parseError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.detail === "string") return body.detail;
    if (Array.isArray(body?.detail) && body.detail[0]?.msg) {
      return body.detail[0].msg;
    }
    return `Request failed with status ${response.status}`;
  } catch {
    return `Request failed with status ${response.status}`;
  }
}

async function request<T>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = init;

  const finalHeaders = new Headers(headers);
  const token = auth ? getToken() : null;
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const isFormData = rest.body instanceof FormData;
  if (rest.body && !isFormData && !finalHeaders.has("Content-Type")) {
    finalHeaders.set("Content-Type", "application/json");
  }

  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, { ...rest, headers: finalHeaders });
  } catch {
    throw new ApiError(
      `Cannot reach the backend at ${BASE_URL}. Is the FastAPI server running?`,
      0,
    );
  }

  if (response.status === 204) return undefined as T;

  if (!response.ok) {
    if (response.status === 401 && auth) clearToken();
    throw new ApiError(await parseError(response), response.status);
  }

  return (await response.json()) as T;
}

// ---------------------------------------------------------------------------
// Endpoints
// ---------------------------------------------------------------------------
export const api = {
  health: () => request<Health>("/health", { auth: false }),

  register: (email: string, password: string, fullName?: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password, full_name: fullName || null }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      auth: false,
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me"),

  listDocuments: () => request<DocumentList>("/documents"),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<UploadedDocument>("/documents", {
      method: "POST",
      body: form,
    });
  },

  deleteDocument: (id: string) =>
    request<void>(`/documents/${id}`, { method: "DELETE" }),

  ask: (question: string, documentIds?: string[]) =>
    request<ChatAnswer>("/chat", {
      method: "POST",
      body: JSON.stringify({
        question,
        top_k: null,
        document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
      }),
    }),

  /**
   * Stream an answer token by token.
   *
   * `onSources` fires as soon as retrieval finishes, so citations can render
   * while the answer is still being generated. `onToken` receives each chunk of
   * text. The backend sends a final `done` event carrying the cleaned answer,
   * which replaces whatever was streamed, because refusal detection can only
   * run once generation completes.
   *
   * Falls back to `ask` if the stream cannot be established or breaks partway,
   * so a proxy that buffers or drops the connection still returns an answer.
   */
  askStream: async (
    question: string,
    documentIds: string[] | undefined,
    handlers: {
      onSources?: (payload: {
        sources: Source[];
        model: string;
      }) => void;
      onToken?: (text: string) => void;
    },
  ): Promise<ChatAnswer> => {
    const token = getToken();
    const headers = new Headers({ "Content-Type": "application/json" });
    if (token) headers.set("Authorization", `Bearer ${token}`);

    let response: Response;
    try {
      response = await fetch(`${BASE_URL}/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          question,
          top_k: null,
          document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
        }),
      });
    } catch {
      return api.ask(question, documentIds);
    }

    // Validation errors (no documents, unknown ids) come back as normal JSON.
    if (!response.ok || !response.body) {
      if (response.status === 401) clearToken();
      return api.ask(question, documentIds);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let started = false;
    let result: ChatAnswer | null = null;

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line.
        let split = buffer.indexOf("\n\n");
        while (split !== -1) {
          const frame = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);
          split = buffer.indexOf("\n\n");

          let event = "message";
          let data = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (!data) continue;

          let parsed: {
            text?: string;
            answer?: string;
            has_context?: boolean;
            model?: string;
            sources?: Source[];
            chart?: Chart | null;
            diagram?: string | null;
          };
          try {
            parsed = JSON.parse(data);
          } catch {
            continue;
          }

          started = true;
          if (event === "sources" && handlers.onSources) {
            handlers.onSources({
              sources: parsed.sources ?? [],
              model: parsed.model ?? "",
            });
          } else if (event === "token" && handlers.onToken && parsed.text) {
            handlers.onToken(parsed.text);
          } else if (event === "done") {
            result = {
              answer: parsed.answer ?? "",
              sources: [],
              has_context: parsed.has_context ?? true,
              model: parsed.model ?? "",
              chart: parsed.chart ?? null,
              diagram: parsed.diagram ?? null,
            };
          }
        }
      }
    } catch {
      // The stream died mid-answer; the buffered endpoint still works.
      return api.ask(question, documentIds);
    } finally {
      reader.releaseLock();
    }

    // `done` never arrived: fall back rather than showing a truncated answer.
    if (!result || !started) {
      return api.ask(question, documentIds);
    }
    return result;
  },

  clearHistory: () => request<void>("/chat/history", { method: "DELETE" }),
};

export { BASE_URL };
