import type { IconName } from "@/components/ui/Icon";

export const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#verification", label: "Verification" },
  { href: "#faq", label: "FAQ" },
];

export const STATS = [
  { value: "100%", label: "of answers grounded in retrieved passages" },
  { value: "Page-level", label: "citations down to the exact page" },
  { value: "Local-first", label: "documents never leave your machine" },
];

export type Feature = {
  icon: IconName;
  title: string;
  body: string;
};

export const FEATURES: Feature[] = [
  {
    icon: "upload",
    title: "Drop in a PDF",
    body: "Drag a file in or pick one from disk. Text is extracted per page and chunked so every passage keeps its true page number.",
  },
  {
    icon: "search",
    title: "Search by meaning",
    body: "Questions are matched with sentence-transformer embeddings, not keywords, so you can ask about an idea instead of the exact wording.",
  },
  {
    icon: "chat",
    title: "Answers as they write",
    body: "Tokens stream in token by token, so the answer is readable while the model is still thinking. Citations attach the moment retrieval finishes.",
  },
  {
    icon: "quote",
    title: "Every claim sourced",
    body: "Each answer links back to the filename, page, similarity score, and the exact snippet that supported it.",
  },
  {
    icon: "shield",
    title: "Refuses when it must",
    body: "The model is told to answer only from context, and to decline when that context is thin. No context means no model call at all.",
  },
  {
    icon: "lock",
    title: "Private per account",
    body: "Every vector is tagged with its owner and every query filters on it, so no account can ever retrieve another's documents.",
  },
];

export const STEPS = [
  {
    title: "Upload and index",
    body: "PyMuPDF pulls the text out page by page. Pages with no text — scanned images — are skipped rather than turned into noise. Overlapping chunks go into a local vector store.",
  },
  {
    title: "Ask in plain language",
    body: "Your question is embedded and compared against your chunks. The closest passages are stitched into a prompt with a strict instruction to use nothing else.",
  },
  {
    title: "Read the answer and the evidence",
    body: "The model answers from that context alone. Alongside the reply you get the source page, the matching snippet, and a similarity score you can weigh yourself.",
  },
];

export const FAQS = [
  {
    q: "What happens if my document does not cover the question?",
    a: "The model is instructed to reply that it could not find an answer in the uploaded documents. That marker is detected server-side and the response is flagged so the interface can warn you, rather than quietly inventing something plausible.",
  },
  {
    q: "Do my documents get sent anywhere?",
    a: "No. Extraction, embedding, retrieval, and generation all run locally — the LLM through Ollama on your own machine. Nothing is uploaded to a third-party service.",
  },
  {
    q: "How accurate are the page numbers?",
    a: "Pages are split and chunked individually rather than concatenated first, so every chunk keeps the page it actually came from. That is what lets a citation point at a specific page instead of a vague region of the file.",
  },
  {
    q: "What happens when I delete a document?",
    a: "The file and its vectors are both removed. Nothing it contributed is left behind in the store, and it stops appearing as retrieval context immediately.",
  },
  {
    q: "Can I scope a question to specific documents?",
    a: "Yes. Tick the documents you care about in the sidebar and retrieval is filtered to just those. With nothing ticked, every ready document is searched.",
  },
];
