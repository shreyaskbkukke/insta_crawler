"""CSV export generation, built on demand from the collected data."""

import csv
import io
import zipfile
from typing import Any, Literal

from .models import Post, utcnow
from .queries import PostFilters, filter_posts
from .store import ProfileRecord

ExportKind = Literal["zip", "posts", "profile"]

PROFILE_COLUMNS = [
    "username", "profile_id", "display_name", "biography", "website", "profile_url",
    "followers_count", "follows_count", "media_count", "fetched_at",
    "collection_status", "collection_complete", "posts_collected", "export_scope",
    "posts_in_export", "exported_at",
]
POST_COLUMNS = [
    "username", "post_id", "post_url", "published_at", "post_type", "caption",
    "like_count", "comment_count", "view_count", "media_count", "collected_at",
]
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def cell(value: Any) -> str:
    """Render a CSV cell: blanks for missing values, and neutralize spreadsheet formulas."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    text = str(value)
    if isinstance(value, str) and text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def _csv(header: list[str], rows) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    writer.writerows([cell(v) for v in row] for row in rows)
    # BOM so Excel detects UTF-8 in captions with emoji/non-Latin text.
    return "﻿".encode() + buf.getvalue().encode()


def posts_csv(username: str, posts: list[Post]) -> bytes:
    return _csv(POST_COLUMNS, (
        (username, p.id, p.permalink, p.published_at, p.post_type.value, p.caption,
         p.like_count, p.comment_count, p.view_count, p.media_count, p.collected_at)
        for p in posts
    ))


def profile_csv(record: ProfileRecord, filters: PostFilters, exported: int) -> bytes:
    p = record.profile
    return _csv(PROFILE_COLUMNS, [(
        p.username, p.id, p.display_name, p.biography, p.website, p.profile_url,
        p.followers_count, p.follows_count, p.media_count, p.fetched_at,
        record.job.status.value if record.job else "not_started", record.ever_completed,
        len(record.posts), f"filtered: {filters.describe()}" if filters.narrowing else "all",
        exported, utcnow(),
    )])


def build_export(record: ProfileRecord, kind: ExportKind, filters: PostFilters) -> tuple[bytes, str, str]:
    """Return (content, media type, filename)."""
    posts = filter_posts(list(record.posts.values()), filters)
    stamp = utcnow().strftime("%Y%m%d-%H%M%S")
    scope = "filtered" if filters.narrowing else "all"
    base = f"{record.profile.username}_{kind}_{scope}_{stamp}"
    match kind:
        case "posts":
            return posts_csv(record.profile.username, posts), "text/csv", f"{base}.csv"
        case "profile":
            return profile_csv(record, filters, len(posts)), "text/csv", f"{base}.csv"
        case _:
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("profile.csv", profile_csv(record, filters, len(posts)))
                zf.writestr("posts.csv", posts_csv(record.profile.username, posts))
            return buf.getvalue(), "application/zip", f"{base}.zip"
