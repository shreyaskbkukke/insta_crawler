import base64
import json
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import Post, PostType


class PostFilters(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sort: Literal["newest", "oldest"] = "newest"
    type: PostType | None = None
    date_from: date | None = Field(None, alias="from")
    date_to: date | None = Field(None, alias="to")
    keyword: str | None = None
    min_likes: int | None = Field(None, ge=0)
    min_comments: int | None = Field(None, ge=0)

    @property
    def narrowing(self) -> bool:
        return bool(self.model_dump(exclude_none=True).keys() - {"sort"})

    def describe(self) -> str:
        parts = [f"{k}={v}" for k, v in self.model_dump(by_alias=True, exclude_none=True).items()]
        return "; ".join(parts)


class InvalidCursorError(ValueError):
    pass


def encode_cursor(post: Post) -> str:
    raw = json.dumps([post.published_at.isoformat(), post.id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        ts, post_id = json.loads(raw)
        return datetime.fromisoformat(ts), str(post_id)
    except Exception as exc:
        raise InvalidCursorError("Invalid cursor") from exc


def _start_of(d: date) -> datetime:
    return datetime.combine(d, time.min, tzinfo=UTC)


def _matches(p: Post, f: PostFilters, keyword: str | None) -> bool:
    if f.type and p.post_type != f.type:
        return False
    if f.date_from and p.published_at < _start_of(f.date_from):
        return False
    if f.date_to and p.published_at >= _start_of(f.date_to + timedelta(days=1)):
        return False
    if keyword and keyword not in (p.caption or "").lower():
        return False
    # Unknown counts (None) never satisfy a minimum.
    if f.min_likes is not None and (p.like_count is None or p.like_count < f.min_likes):
        return False
    if f.min_comments is not None and (p.comment_count is None or p.comment_count < f.min_comments):
        return False
    return True


def filter_posts(posts: list[Post], f: PostFilters) -> list[Post]:
    """Filter and sort the whole collection by the stable key (published_at, id)."""
    keyword = (f.keyword or "").strip().lower() or None
    matched = [p for p in posts if _matches(p, f, keyword)]
    matched.sort(key=lambda p: (p.published_at, p.id), reverse=f.sort == "newest")
    return matched


def page_posts(
    posts: list[Post], f: PostFilters, cursor: str | None, limit: int
) -> tuple[list[Post], str | None, int]:
    """Keyset pagination: pages stay consistent while collection adds new posts."""
    matched = filter_posts(posts, f)
    total = len(matched)
    if cursor:
        key = decode_cursor(cursor)
        if f.sort == "newest":
            matched = [p for p in matched if (p.published_at, p.id) < key]
        else:
            matched = [p for p in matched if (p.published_at, p.id) > key]
    page = matched[:limit]
    next_cursor = encode_cursor(page[-1]) if len(matched) > limit else None
    return page, next_cursor, total
