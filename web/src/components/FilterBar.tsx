"use client";

import { useEffect, useState } from "react";
import { EMPTY_FILTERS, type Filters } from "@/lib/api";

const field =
  "rounded-md border border-black/15 bg-white px-2.5 py-1.5 text-sm dark:border-white/15 dark:bg-neutral-900";

export function FilterBar({ filters, onChange }: { filters: Filters; onChange: (f: Filters) => void }) {
  // Text inputs are debounced so typing doesn't refetch on every keystroke.
  const [keyword, setKeyword] = useState(filters.keyword);
  const [prevKeyword, setPrevKeyword] = useState(filters.keyword);
  if (filters.keyword !== prevKeyword) {
    // External change (e.g. "Clear filters" or back navigation): sync the input.
    setPrevKeyword(filters.keyword);
    setKeyword(filters.keyword);
  }
  useEffect(() => {
    if (keyword === filters.keyword) return;
    const t = setTimeout(() => onChange({ ...filters, keyword }), 400);
    return () => clearTimeout(t);
  }, [keyword, filters, onChange]);

  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });
  const dirty = JSON.stringify({ ...filters, sort: "newest" }) !== JSON.stringify(EMPTY_FILTERS);

  return (
    <div className="flex flex-wrap items-end gap-3">
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        Sort
        <select className={field} value={filters.sort} onChange={(e) => set("sort", e.target.value as Filters["sort"])}>
          <option value="newest">Newest first</option>
          <option value="oldest">Oldest first</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        Type
        <select className={field} value={filters.type} onChange={(e) => set("type", e.target.value as Filters["type"])}>
          <option value="">All types</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="reel">Reel</option>
          <option value="carousel">Carousel</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        From
        <input type="date" className={field} value={filters.from} onChange={(e) => set("from", e.target.value)} />
      </label>
      <label className="flex flex-col gap-1 text-xs text-neutral-500">
        To
        <input type="date" className={field} value={filters.to} onChange={(e) => set("to", e.target.value)} />
      </label>
      <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs text-neutral-500">
        Caption keyword
        <input
          type="search"
          className={field}
          placeholder="Search captions"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </label>
      <label className="flex w-28 flex-col gap-1 text-xs text-neutral-500">
        Min likes
        <input
          type="number"
          min={0}
          className={field}
          value={filters.min_likes}
          onChange={(e) => set("min_likes", e.target.value)}
        />
      </label>
      <label className="flex w-28 flex-col gap-1 text-xs text-neutral-500">
        Min comments
        <input
          type="number"
          min={0}
          className={field}
          value={filters.min_comments}
          onChange={(e) => set("min_comments", e.target.value)}
        />
      </label>
      {dirty && (
        <button
          onClick={() => onChange({ ...EMPTY_FILTERS, sort: filters.sort })}
          className="py-1.5 text-sm text-neutral-500 hover:text-neutral-900 dark:hover:text-white"
        >
          Clear filters
        </button>
      )}
    </div>
  );
}
