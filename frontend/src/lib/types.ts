export type User = {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
};

export type TokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: User;
};

export type DocumentStatus = "ready" | "processing" | "failed";

export type UploadedDocument = {
  id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  size_bytes: number;
  status: DocumentStatus;
  created_at: string;
};

export type DocumentList = {
  documents: UploadedDocument[];
  total: number;
};

export type Source = {
  document_id: string;
  filename: string;
  page: number;
  chunk_index: number;
  snippet: string;
  score: number;
};

export type Chart = {
  type: "bar" | "hbar" | "line" | "pie";
  title: string;
  data: { label: string; value: number }[];
};

export type ChatAnswer = {
  answer: string;
  sources: Source[];
  has_context: boolean;
  model: string;
  chart?: Chart | null;
  diagram?: string | null;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources: Source[];
  hasContext?: boolean;
  model?: string;
  /** True while tokens are still streaming in for this message. */
  streaming?: boolean;
  chart?: Chart | null;
  diagram?: string | null;
};

export type Health = {
  status: string;
  llm: string;
  embedding_model: string;
  vector_store: string;
  documents: number;
  details: Record<string, unknown>;
};

export const SUGGESTED_QUESTIONS = [
  "What is the main topic of this document?",
  "Summarise the key findings.",
  "What methodology was used?",
  "List the limitations mentioned.",
];
