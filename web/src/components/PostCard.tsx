"use client";

import { useState } from "react";
import { fmtCount, fmtDate, type Post } from "@/lib/api";

export function PostCard({ post }: { post: Post }) {
  // Instagram CDN URLs expire; fall back to a placeholder rather than a broken image.
  const [broken, setBroken] = useState(false);

  return (
    <article className="flex flex-col overflow-hidden rounded-lg border border-black/10 bg-white dark:border-white/10 dark:bg-neutral-900">
      <a href={post.permalink} target="_blank" rel="noopener noreferrer" className="relative block aspect-square">
        {post.thumbnail_url && !broken ? (
          <img
            src={post.thumbnail_url}
            alt={post.caption?.slice(0, 100) ?? ""}
            loading="lazy"
            referrerPolicy="no-referrer"
            onError={() => setBroken(true)}
            className="size-full bg-neutral-100 object-cover dark:bg-neutral-800"
          />
        ) : (
          <div className="flex size-full items-center justify-center bg-neutral-100 text-xs text-neutral-400 dark:bg-neutral-800">
            Preview unavailable
          </div>
        )}
        <span className="absolute left-2 top-2 rounded bg-black/60 px-1.5 py-0.5 text-[11px] font-medium capitalize text-white">
          {post.post_type}
          {post.post_type === "carousel" && ` · ${post.media_count}`}
        </span>
      </a>
      <div className="flex flex-1 flex-col gap-2 p-3">
        <time dateTime={post.published_at} className="text-xs text-neutral-500">
          {fmtDate(post.published_at)}
        </time>
        <p className="line-clamp-3 text-sm">
          {post.caption ?? <span className="italic text-neutral-400">No caption</span>}
        </p>
        <div className="mt-auto flex items-center justify-between pt-1 text-xs text-neutral-600 dark:text-neutral-400">
          <span className="flex gap-3">
            <span title={post.like_count == null ? "Like count hidden or unavailable" : undefined}>
              ♥ {fmtCount(post.like_count)}
            </span>
            <span>💬 {fmtCount(post.comment_count)}</span>
            {post.view_count != null && <span>▶ {fmtCount(post.view_count)}</span>}
          </span>
          <a
            href={post.permalink}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-blue-600 hover:underline dark:text-blue-400"
          >
            Open ↗
          </a>
        </div>
      </div>
    </article>
  );
}
