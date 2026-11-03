from dataclasses import dataclass
from typing import Protocol

from ..models import Post, Profile


@dataclass(slots=True)
class PostPage:
    posts: list[Post]
    # Cursor for the following page, or None when the source has no more posts.
    next_cursor: str | None


class DataSourceError(Exception):
    """Base error. `transient` errors are retried by the collector."""

    transient = False


class TransientError(DataSourceError):
    transient = True


class RateLimitedError(TransientError):
    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class ProfileNotFoundError(DataSourceError):
    pass


class AuthError(DataSourceError):
    pass


class DataSource(Protocol):
    name: str

    async def fetch_profile(self, username: str) -> Profile: ...

    async def fetch_posts(self, username: str, cursor: str | None) -> PostPage: ...

    async def aclose(self) -> None: ...
