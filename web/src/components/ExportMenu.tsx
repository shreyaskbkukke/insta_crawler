import { api, type Filters } from "@/lib/api";

const btn =
  "rounded-md border border-black/15 px-3 py-1.5 text-sm hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/5";

export function ExportMenu({
  username,
  filters,
  filtered,
  incomplete,
}: {
  username: string;
  filters: Filters;
  filtered: boolean;
  incomplete: boolean;
}) {
  // "All" downloads keep the chosen sort order but drop the narrowing filters.
  const all: Filters = { type: "", from: "", to: "", keyword: "", min_likes: "", min_comments: "", sort: filters.sort };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-sm text-neutral-500">Download:</span>
      <a className={btn} href={api.exportUrl(username, "zip", all)} download>
        All data (ZIP)
      </a>
      <a className={btn} href={api.exportUrl(username, "posts", all)} download>
        All posts.csv
      </a>
      {filtered && (
        <a className={btn} href={api.exportUrl(username, "posts", filters)} download>
          Filtered posts.csv
        </a>
      )}
      <a className={btn} href={api.exportUrl(username, "profile", all)} download>
        profile.csv
      </a>
      {incomplete && (
        <span className="text-xs text-amber-700 dark:text-amber-400">
          Collection isn&apos;t complete yet; downloads include what&apos;s collected so far.
        </span>
      )}
    </div>
  );
}
