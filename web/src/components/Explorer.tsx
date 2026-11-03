"use client";

import { useParams, usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiError, EMPTY_FILTERS, api, type Filters, type Post, type ProfileDetail } from "@/lib/api";
import { CollectionStatus } from "./CollectionStatus";
import { ExportMenu } from "./ExportMenu";
import { FilterBar } from "./FilterBar";
import { PostCard } from "./PostCard";
import { ProfileHeader } from "./ProfileHeader";

const PAGE_SIZE = 24;
const POLL_MS = 2000;

export function Explorer() {
  const { username } = useParams<{ username: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Filters live in the URL so a filtered view can be shared or bookmarked.
  const filters = useMemo<Filters>(() => {
    const f = { ...EMPTY_FILTERS };
    for (const key of Object.keys(f) as (keyof Filters)[]) {
      const v = searchParams.get(key);
      if (v != null) (f as Record<string, string>)[key] = v;
    }
    return f;
  }, [searchParams]);
  const filtered = Object.entries(filters).some(([k, v]) => k !== "sort" && v !== "");

  const setFilters = useCallback(
    (f: Filters) => {
      const params = new URLSearchParams(Object.entries(f).filter(([k, v]) => v !== "" && !(k === "sort" && v === "newest")));
      router.replace(params.size ? `${pathname}?${params}` : pathname, { scroll: false });
    },
    [router, pathname],
  );

  const [detail, setDetail] = useState<ProfileDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  const [posts, setPosts] = useState<Post[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  // The filter key whose first page is currently shown; differs from `filterKey` while loading.
  const filterKey = searchParams.toString();
  const [shownKey, setShownKey] = useState<string | null>(null);
  const loadingFirst = shownKey !== filterKey;
  const pagesLoaded = useRef(0);
  const requestId = useRef(0);
  const lastCollected = useRef<number | undefined>(undefined);

  const showError = useCallback((err: unknown) => setError(err instanceof Error ? err.message : String(err)), []);

  const fetchFirstPage = useCallback(() => {
    const id = ++requestId.current;
    api.posts(username, filters, null, PAGE_SIZE).then((page) => {
      if (id !== requestId.current) return; // superseded by a newer filter change
      setPosts(page.items);
      setCursor(page.next_cursor);
      setTotal(page.total);
      setShownKey(filterKey);
      pagesLoaded.current = 1;
    }, (err) => {
      if (id === requestId.current && !(err instanceof ApiError && err.status === 404)) showError(err);
    });
  }, [username, filters, filterKey, showError]);

  const fetchDetail = useCallback(() => {
    api.profile(username).then((d) => {
      setDetail(d);
      setNotFound(false);
      // New posts show up live while the user is on the first page; once they've
      // scrolled further only the total updates, so the list doesn't jump.
      const collected = d.collection.posts_collected;
      if (collected !== lastCollected.current && pagesLoaded.current <= 1) {
        fetchFirstPage();
      }
      lastCollected.current = collected;
    }, (err) => {
      if (err instanceof ApiError && err.status === 404) setNotFound(true);
      else showError(err);
    });
  }, [username, fetchFirstPage, showError]);

  const loadMore = useCallback(async () => {
    if (!cursor || loadingMore || loadingFirst) return;
    const id = requestId.current;
    setLoadingMore(true);
    try {
      const page = await api.posts(username, filters, cursor, PAGE_SIZE);
      if (id !== requestId.current) return;
      setPosts((prev) => [...prev, ...page.items]);
      setCursor(page.next_cursor);
      setTotal(page.total);
      pagesLoaded.current += 1;
    } catch (err) {
      showError(err);
    } finally {
      setLoadingMore(false);
    }
  }, [username, filters, cursor, loadingMore, loadingFirst, showError]);

  useEffect(fetchFirstPage, [fetchFirstPage]);

  // Poll while collecting.
  const status = detail?.collection.status;
  const active = status === "queued" || status === "running";
  useEffect(() => {
    fetchDetail();
    if (!active) return;
    const t = setInterval(fetchDetail, POLL_MS);
    return () => clearInterval(t);
  }, [active, fetchDetail]);

  // Infinite scroll: load the next page when the sentinel enters the viewport.
  const sentinel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = sentinel.current;
    if (!el) return;
    const obs = new IntersectionObserver((entries) => entries[0].isIntersecting && loadMore(), {
      rootMargin: "600px",
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loadMore]);

  async function startCollection() {
    setStarting(true);
    setError(null);
    try {
      await api.startCollection(username);
      fetchDetail();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setStarting(false);
    }
  }

  if (notFound) {
    return (
      <div className="mx-auto max-w-md pt-16 text-center">
        <h1 className="text-xl font-semibold">@{username} hasn&apos;t been collected yet</h1>
        <button
          onClick={startCollection}
          disabled={starting}
          className="mt-4 rounded-lg bg-neutral-900 px-5 py-2.5 font-medium text-white disabled:opacity-50 dark:bg-white dark:text-neutral-900"
        >
          {starting ? "Looking up…" : "Start collecting"}
        </button>
        {error && <p className="mt-3 text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    );
  }

  if (!detail) {
    return error ? <p className="text-red-600">{error}</p> : <p className="text-neutral-500">Loading…</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <ProfileHeader profile={detail.profile} />
      <CollectionStatus detail={detail} onStart={startCollection} starting={starting} />
      {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

      <section className="flex flex-col gap-4">
        <FilterBar filters={filters} onChange={setFilters} />
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-black/10 pb-3 dark:border-white/10">
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            {filtered ? (
              <>
                <b>{total.toLocaleString()}</b> of {detail.collection.posts_collected.toLocaleString()} posts match
              </>
            ) : (
              <>
                <b>{total.toLocaleString()}</b> posts
              </>
            )}
          </p>
          <ExportMenu
            username={detail.profile.username}
            filters={filters}
            filtered={filtered}
            incomplete={!detail.collection.complete}
          />
        </div>

        {posts.length === 0 && !loadingFirst ? (
          <p className="py-16 text-center text-neutral-500">
            {active ? "Collecting posts…" : filtered ? "No posts match these filters." : "No posts collected."}
          </p>
        ) : (
          <div
            className={`grid grid-cols-2 gap-4 transition-opacity sm:grid-cols-3 lg:grid-cols-4 ${loadingFirst ? "opacity-50" : ""}`}
          >
            {posts.map((p) => (
              <PostCard key={p.id} post={p} />
            ))}
          </div>
        )}

        <div ref={sentinel} />
        {cursor && (
          <button
            onClick={loadMore}
            disabled={loadingMore}
            className="mx-auto rounded-md border border-black/15 px-4 py-2 text-sm hover:bg-black/5 disabled:opacity-50 dark:border-white/15 dark:hover:bg-white/5"
          >
            {loadingMore ? "Loading…" : "Load more"}
          </button>
        )}
      </section>
    </div>
  );
}
