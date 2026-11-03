export type PostType = "image" | "video" | "reel" | "carousel";
export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface Profile {
  id: string;
  username: string;
  display_name: string | null;
  biography: string | null;
  website: string | null;
  profile_url: string;
  profile_picture_url: string | null;
  followers_count: number | null;
  follows_count: number | null;
  media_count: number | null;
  fetched_at: string;
}

export interface CollectionJob {
  id: number;
  status: JobStatus;
  retrieved_count: number;
  reached_end: boolean;
  error: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  username: string;
}

export interface ProfileDetail {
  profile: Profile;
  collection: {
    status: JobStatus | "not_started";
    posts_collected: number;
    posts_reported: number | null;
    complete: boolean;
    limitations: string[];
    job: CollectionJob | null;
  };
}

export interface Post {
  id: string;
  permalink: string;
  caption: string | null;
  published_at: string;
  post_type: PostType;
  like_count: number | null;
  comment_count: number | null;
  view_count: number | null;
  thumbnail_url: string | null;
  media_count: number;
  collected_at: string;
}

export interface PostPage {
  items: Post[];
  next_cursor: string | null;
  total: number;
}

export interface Filters {
  sort: "newest" | "oldest";
  type: PostType | "";
  from: string;
  to: string;
  keyword: string;
  min_likes: string;
  min_comments: string;
}

export const EMPTY_FILTERS: Filters = {
  sort: "newest",
  type: "",
  from: "",
  to: "",
  keyword: "",
  min_likes: "",
  min_comments: "",
};

export type ExportKind = "zip" | "posts" | "profile";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
    } catch {}
    throw new ApiError(res.status, message);
  }
  return res.json();
}

/** Only the filters the user actually set, keyed as the API expects. */
export function activeFilters(f: Filters): Record<string, string> {
  return Object.fromEntries(Object.entries(f).filter(([, v]) => v !== "" && v != null));
}

export const api = {
  startCollection: (username: string) =>
    request<CollectionJob>("/api/collections", { method: "POST", body: JSON.stringify({ username }) }),

  profile: (username: string) => request<ProfileDetail>(`/api/profiles/${encodeURIComponent(username)}`),

  posts: (username: string, filters: Filters, cursor: string | null, limit = 24) => {
    const params = new URLSearchParams({ ...activeFilters(filters), limit: String(limit) });
    if (cursor) params.set("cursor", cursor);
    return request<PostPage>(`/api/profiles/${encodeURIComponent(username)}/posts?${params}`);
  },

  /** Direct download URL; served by the backend as an attachment. */
  exportUrl: (username: string, kind: ExportKind, filters: Filters) =>
    `/api/profiles/${encodeURIComponent(username)}/export?${new URLSearchParams({ ...activeFilters(filters), kind })}`,
};

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });
export const fmtCount = (n: number | null | undefined) => (n == null ? "—" : compact.format(n));
export const fmtDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en", { year: "numeric", month: "short", day: "numeric" });
