export default function Loading() {
  return (
    <div className="flex h-dvh flex-col overflow-hidden" aria-busy="true">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-line bg-card px-3 sm:px-4">
        <div className="animate-shimmer size-8 rounded-lg" />
        <div className="animate-shimmer h-3.5 w-24 rounded" />
        <div className="animate-shimmer ml-auto h-8 w-32 rounded-lg" />
      </header>
      <main className="flex min-h-0 flex-1 gap-4 p-3 sm:p-4">
        <div className="animate-shimmer hidden w-72 shrink-0 rounded-2xl lg:block" />
        <div className="animate-shimmer min-w-0 flex-1 rounded-2xl" />
      </main>
    </div>
  );
}
