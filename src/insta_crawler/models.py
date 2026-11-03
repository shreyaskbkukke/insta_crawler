import enum
from datetime import UTC, datetime

from pydantic import BaseModel, Field, computed_field


def utcnow() -> datetime:
    return datetime.now(UTC)


class PostType(enum.StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    REEL = "reel"
    CAROUSEL = "carousel"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Profile(BaseModel):
    id: str
    username: str
    display_name: str | None = None
    biography: str | None = None
    website: str | None = None
    profile_picture_url: str | None = None
    followers_count: int | None = None
    follows_count: int | None = None
    media_count: int | None = None
    fetched_at: datetime = Field(default_factory=utcnow)

    @computed_field
    @property
    def profile_url(self) -> str:
        return f"https://www.instagram.com/{self.username}/"


class Media(BaseModel):
    position: int
    media_type: str
    media_url: str | None = None


class Post(BaseModel):
    id: str
    permalink: str
    published_at: datetime
    post_type: PostType
    caption: str | None = None
    # None means unavailable (e.g. hidden likes) and is exported as blank, never 0.
    like_count: int | None = None
    comment_count: int | None = None
    view_count: int | None = None
    thumbnail_url: str | None = None
    media: list[Media] = Field(default_factory=list)
    collected_at: datetime = Field(default_factory=utcnow)

    @computed_field
    @property
    def media_count(self) -> int:
        return len(self.media) or 1


class CollectionJob(BaseModel):
    id: int
    status: JobStatus = JobStatus.QUEUED
    # Pagination checkpoint: the cursor of the *next* page to fetch.
    cursor: str | None = None
    retrieved_count: int = 0
    reached_end: bool = False
    error: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None
