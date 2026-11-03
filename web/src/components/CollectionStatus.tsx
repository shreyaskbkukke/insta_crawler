import type { ProfileDetail } from "@/lib/api";

const LABELS = {
  not_started: "Not collected",
  queued: "Queued",
  running: "Collecting",
  completed: "Collected",
  failed: "Stopped",
} as const;

export function CollectionStatus({
  detail,
  onStart,
  starting,
}: {
  detail: ProfileDetail;
  onStart: () => void;
  starting: boolean;
}) {
  const c = detail.collection;
  const active = c.status === "queued" || c.status === "running";
  const pct = c.posts_reported ? Math.min(100, (c.posts_collected / c.posts_reported) * 100) : null;
  const action = c.status === "failed" ? "Resume collection" : c.complete ? "Refresh" : "Start collection";

  return (
    <div className="rounded-lg border border-black/10 p-4 dark:border-white/10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="text-sm">
          <span
            className={`mr-2 inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
              c.status === "failed"
                ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                : active
                  ? "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300"
                  : "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300"
            }`}
          >
            {LABELS[c.status]}
          </span>
          <b>{c.posts_collected.toLocaleString()}</b>
          {c.posts_reported != null && <> of {c.posts_reported.toLocaleString()}</>} posts collected
          {!active && c.posts_collected > 0 && (
            <span className="ml-2 text-neutral-500">· {c.complete ? "complete" : "partial"}</span>
          )}
        </div>
        {!active && (
          <button
            onClick={onStart}
            disabled={starting}
            className="rounded-md border border-black/15 px-3 py-1.5 text-sm hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5"
          >
            {starting ? "Starting…" : action}
          </button>
        )}
      </div>
      {active && pct != null && (
        <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800">
          <div className="h-full bg-blue-600 transition-all" style={{ width: `${pct}%` }} />
        </div>
      )}
      {c.limitations.map((note) => (
        <p key={note} className="mt-2 text-sm text-amber-700 dark:text-amber-400">
          {note}
        </p>
      ))}
    </div>
  );
}
