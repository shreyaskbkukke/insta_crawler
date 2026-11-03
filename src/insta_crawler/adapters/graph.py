"""Instagram Graph API adapter using Business Discovery.

Business Discovery lets an Instagram Business/Creator account (identified by
`ig_user_id`) read public data about *other* Business/Creator accounts by
username. Personal accounts are not reachable through this API.
"""

from datetime import datetime

import httpx

from ..models import Media, Post, PostType, Profile
from .base import (
    AuthError,
    DataSourceError,
    PostPage,
    ProfileNotFoundError,
    RateLimitedError,
    TransientError,
)

PROFILE_FIELDS = (
    "id,username,name,biography,website,profile_picture_url,followers_count,follows_count,media_count"
)
MEDIA_FIELDS = (
    "id,caption,timestamp,media_type,media_product_type,permalink,like_count,comments_count,"
    "media_url,thumbnail_url,children{id,media_type,media_url,thumbnail_url}"
)

RATE_LIMIT_CODES = {4, 17, 32, 613, 80001, 80002}
AUTH_CODES = {102, 190}
NOT_FOUND_CODES = {100, 110}


def _post_type(item: dict) -> PostType:
    if item.get("media_product_type") == "REELS":
        return PostType.REEL
    match item.get("media_type"):
        case "CAROUSEL_ALBUM":
            return PostType.CAROUSEL
        case "VIDEO":
            return PostType.VIDEO
        case _:
            return PostType.IMAGE


def _preview_url(item: dict) -> str | None:
    return item.get("thumbnail_url") or item.get("media_url")


def parse_post(item: dict) -> Post:
    children = (item.get("children") or {}).get("data") or []
    media = [
        Media(position=i, media_type=c.get("media_type", "IMAGE"), media_url=c.get("media_url"))
        for i, c in enumerate(children)
    ] or [Media(position=0, media_type=item.get("media_type", "IMAGE"), media_url=item.get("media_url"))]
    thumbnail = _preview_url(item) or next((_preview_url(c) for c in children if _preview_url(c)), None)
    return Post(
        id=item["id"],
        permalink=item["permalink"],
        published_at=datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%S%z"),
        post_type=_post_type(item),
        caption=item.get("caption"),
        # Absent when the owner hides likes: keep as None rather than 0.
        like_count=item.get("like_count"),
        comment_count=item.get("comments_count"),
        view_count=None,  # Not exposed by Business Discovery.
        thumbnail_url=thumbnail,
        media=media,
    )


class GraphAPIDataSource:
    name = "graph"

    def __init__(self, access_token: str, ig_user_id: str, api_version: str, page_size: int = 25):
        if not access_token or not ig_user_id:
            raise ValueError("IG_ACCESS_TOKEN and IG_USER_ID must be set (see README: Instagram access)")
        self._token = access_token
        self._ig_user_id = ig_user_id
        self._page_size = page_size
        self._client = httpx.AsyncClient(base_url=f"https://graph.facebook.com/{api_version}", timeout=30)

    async def _discover(self, username: str, fields: str) -> dict:
        params = {
            "fields": f"business_discovery.username({username}){{{fields}}}",
            "access_token": self._token,
        }
        try:
            resp = await self._client.get(f"/{self._ig_user_id}", params=params)
        except httpx.HTTPError as exc:
            raise TransientError(f"Network error talking to Graph API: {exc}") from exc

        if resp.status_code >= 500:
            raise TransientError(f"Graph API returned HTTP {resp.status_code}")
        body = resp.json()
        if "error" in body:
            self._raise_for_error(body["error"], username)
        return body["business_discovery"]

    @staticmethod
    def _raise_for_error(err: dict, username: str) -> None:
        code = err.get("code")
        message = err.get("error_user_msg") or err.get("message", "Unknown Graph API error")
        if code in RATE_LIMIT_CODES:
            raise RateLimitedError(f"Rate limited by Graph API: {message}")
        if code in AUTH_CODES:
            raise AuthError(f"Graph API access token rejected: {message}")
        if code in NOT_FOUND_CODES:
            raise ProfileNotFoundError(
                f"@{username} was not found or is not a Business/Creator account ({message})"
            )
        if err.get("is_transient"):
            raise TransientError(message)
        raise DataSourceError(message)

    async def fetch_profile(self, username: str) -> Profile:
        d = await self._discover(username, PROFILE_FIELDS)
        return Profile(
            id=d["id"],
            username=d["username"].lower(),
            display_name=d.get("name"),
            biography=d.get("biography"),
            website=d.get("website"),
            profile_picture_url=d.get("profile_picture_url"),
            followers_count=d.get("followers_count"),
            follows_count=d.get("follows_count"),
            media_count=d.get("media_count"),
        )

    async def fetch_posts(self, username: str, cursor: str | None) -> PostPage:
        edge = f"media.limit({self._page_size})"
        if cursor:
            edge += f".after({cursor})"
        d = await self._discover(username, f"{edge}{{{MEDIA_FIELDS}}}")
        media = d.get("media") or {}
        items = media.get("data") or []
        paging = media.get("paging") or {}
        after = (paging.get("cursors") or {}).get("after")
        has_more = bool(items) and bool(after) and ("next" in paging or len(items) >= self._page_size)
        return PostPage(posts=[parse_post(i) for i in items], next_cursor=after if has_more else None)

    async def aclose(self) -> None:
        await self._client.aclose()
