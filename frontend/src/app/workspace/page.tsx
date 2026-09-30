import type { Metadata } from "next";
import RagAssistant from "@/components/workspace/RagAssistant";

export const metadata: Metadata = {
  title: "Workspace",
  description:
    "Upload PDFs, ask questions, and read the exact page each answer came from.",
  robots: { index: false },
};

export default function WorkspacePage() {
  return <RagAssistant />;
}
