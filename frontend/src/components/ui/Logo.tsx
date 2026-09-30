import Icon from "./Icon";
import { cx } from "@/lib/cx";

export default function Logo({
  className,
  showWordmark = true,
}: {
  className?: string;
  showWordmark?: boolean;
}) {
  return (
    <span className={cx("inline-flex items-center gap-2.5", className)}>
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-linear-to-br from-brand-400 to-accent-500 text-white shadow-md shadow-brand-600/25">
        <Icon name="sparkles" className="size-[1.15rem]" strokeWidth={1.9} />
      </span>
      {showWordmark && (
        <span className="shrink-0 text-[0.9375rem] leading-none font-semibold tracking-tight whitespace-nowrap">
          RAG Assistant
        </span>
      )}
    </span>
  );
}
