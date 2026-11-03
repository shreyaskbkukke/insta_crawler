"""Deterministic fake data source for tests (no Instagram access)."""

import asyncio
import hashlib
import random
from datetime import UTC, datetime, timedelta

from insta_crawler.models import Media, Post, PostType, Profile
from insta_crawler.adapters.base import PostPage, ProfileNotFoundError, TransientError

WORDS = (
    "sunset coffee travel studio launch behind the scenes new collection weekend city "
    "morning design summer team recipe community thank you announcement giveaway"
).split()


def _seed(username: str) -> int:
    return int(hashlib.sha256(username.encode()).hexdigest()[:8], 16)


class FakeDataSource:
    name = "fake"

    def __init__(self, page_size: int = 25, delay: float = 0.3, fail_every: int = 0):
        self.page_size = page_size
        self.delay = delay
        # Raise a transient error on every Nth fetch_posts call (0 disables).
        self.fail_every = fail_every
        self.calls = 0

    def _post_total(self, username: str) -> int:
        if username.startswith("tiny"):
            return 7
        return 60 + _seed(username) % 240

    async def fetch_profile(self, username: str) -> Profile:
        await asyncio.sleep(self.delay / 3)
        if username.startswith("notfound") or username.startswith("personal"):
            raise ProfileNotFoundError(f"@{username} was not found or is not a Business/Creator account")
        seed = _seed(username)
        return Profile(
            id=f"fake-{seed}",
            username=username,
            display_name=username.replace("_", " ").replace(".", " ").title(),
            biography=f"Fake profile for @{username}.",
            website="https://www.instagram.com/",
            profile_picture_url=f"https://cdn.test/{username}/avatar.jpg",
            followers_count=1000 + seed % 500_000,
            follows_count=seed % 2000,
            media_count=self._post_total(username),
        )

    def _make_post(self, username: str, index: int) -> Post:
        # index 0 is the newest post, like the real API.
        rng = random.Random(f"{username}:{index}")
        seed = _seed(username)
        total = self._post_total(username)
        newest = datetime(2026, 10, 30, 18, tzinfo=UTC)
        published = newest - timedelta(days=(index * 1100) / total, minutes=rng.randint(0, 600))
        post_type = rng.choice(list(PostType))
        post_id = f"{seed}{total - index:05d}"
        n_media = rng.randint(2, 6) if post_type is PostType.CAROUSEL else 1
        media_kind = "VIDEO" if post_type in (PostType.VIDEO, PostType.REEL) else "IMAGE"
        media = [
            Media(position=i, media_type=media_kind, media_url=f"https://cdn.test/{post_id}/{i}.jpg")
            for i in range(n_media)
        ]
        caption = " ".join(rng.choices(WORDS, k=rng.randint(4, 18))).capitalize()
        if rng.random() < 0.3:
            caption += f" #{rng.choice(WORDS)} #{username}"
        return Post(
            id=post_id,
            permalink=f"https://www.instagram.com/p/FAKE{post_id}/",
            published_at=published,
            post_type=post_type,
            caption=caption if rng.random() > 0.05 else None,
            like_count=None if rng.random() < 0.1 else rng.randint(10, 50_000),
            comment_count=rng.randint(0, 2_000),
            view_count=rng.randint(500, 900_000) if post_type is PostType.REEL else None,
            thumbnail_url=f"https://cdn.test/{post_id}/thumb.jpg",
            media=media,
        )

    async def fetch_posts(self, username: str, cursor: str | None) -> PostPage:
        await asyncio.sleep(self.delay)
        self.calls += 1
        if self.fail_every and self.calls % self.fail_every == 0:
            raise TransientError("Simulated transient failure")
        start = int(cursor or 0)
        end = min(start + self.page_size, self._post_total(username))
        posts = [self._make_post(username, i) for i in range(start, end)]
        return PostPage(posts=posts, next_cursor=str(end) if end < self._post_total(username) else None)

    async def aclose(self) -> None:
        pass
