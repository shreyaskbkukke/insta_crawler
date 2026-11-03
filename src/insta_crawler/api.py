from datetime import date, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from .adapters.base import AuthError, DataSourceError, ProfileNotFoundError, TransientError
from .exports import ExportKind, build_export
from .models import CollectionJob, Post, PostType, Profile
from .queries import InvalidCursorError, PostFilters, page_posts
from .store import ProfileRecord
from .usernames import parse_username

router = APIRouter(prefix="/api")


class CollectionRequest(BaseModel):
    username: str = Field(description="Instagram username, @handle, or profile URL")


class CollectionOut(CollectionJob):
    username: str


class CollectionSummary(BaseModel):
    status: str  # not_started | queued | running | completed | failed
    posts_collected: int
    posts_reported: int | None
    complete: bool
    limitations: list[str]
    job: CollectionOut | None


class ProfileDetail(BaseModel):
    profile: Profile
    collection: CollectionSummary


class PostPageOut(BaseModel):
    items: list[Post]
    next_cursor: str | None
    total: int


def collection_out(record: ProfileRecord) -> CollectionOut:
    return CollectionOut(**record.job.model_dump(), username=record.profile.username)


def summarize(record: ProfileRecord) -> CollectionSummary:
    job, collected, reported = record.job, len(record.posts), record.profile.media_count
    notes = []
    if job and job.error:
        notes.append(f"Last collection stopped early: {job.error}. Start it again to resume.")
    if record.ever_completed and reported and collected < reported:
        notes.append(
            f"The data source returned {collected} of {reported} posts reported on the profile; "
            "the rest are not accessible through it."
        )
    return CollectionSummary(
        status=job.status.value if job else "not_started",
        posts_collected=collected,
        posts_reported=reported,
        complete=record.ever_completed,
        limitations=notes,
        job=collection_out(record) if job else None,
    )


def get_record(request: Request, raw: str) -> ProfileRecord:
    username = parse_username(raw)
    record = username and request.app.state.store.get(username)
    if not record:
        raise HTTPException(404, f"Profile @{raw} has not been collected yet")
    return record


def post_filters(
    sort: Literal["newest", "oldest"] = "newest",
    type: PostType | None = None,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
    keyword: str | None = None,
    min_likes: Annotated[int | None, Query(ge=0)] = None,
    min_comments: Annotated[int | None, Query(ge=0)] = None,
) -> PostFilters:
    return PostFilters(
        sort=sort, type=type, date_from=date_from, date_to=date_to,
        keyword=keyword or None, min_likes=min_likes, min_comments=min_comments,
    )


Filters = Annotated[PostFilters, Depends(post_filters)]


@router.post("/collections", response_model=CollectionOut, status_code=202)
async def start_collection(body: CollectionRequest, request: Request):
    username = parse_username(body.username)
    if not username:
        raise HTTPException(422, "Enter a valid Instagram username or profile URL")
    try:
        profile = await request.app.state.source.fetch_profile(username)
    except ProfileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    except TransientError as exc:
        raise HTTPException(503, f"Data source temporarily unavailable: {exc}")
    except (AuthError, DataSourceError) as exc:
        raise HTTPException(502, str(exc))
    record = await request.app.state.store.upsert_profile(profile)
    await request.app.state.collector.start(record)
    return collection_out(record)


@router.get("/collections/{job_id}", response_model=CollectionOut)
async def get_collection(job_id: int, request: Request):
    record = request.app.state.store.find_job(job_id)
    if not record:
        raise HTTPException(404, "Collection job not found")
    return collection_out(record)


@router.get("/profiles/{username}", response_model=ProfileDetail)
async def get_profile(username: str, request: Request):
    record = get_record(request, username)
    return ProfileDetail(profile=record.profile, collection=summarize(record))


@router.get("/profiles/{username}/posts", response_model=PostPageOut)
async def list_posts(
    username: str,
    request: Request,
    filters: Filters,
    cursor: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 24,
):
    record = get_record(request, username)
    try:
        items, next_cursor, total = page_posts(list(record.posts.values()), filters, cursor, limit)
    except InvalidCursorError as exc:
        raise HTTPException(400, str(exc))
    return PostPageOut(items=items, next_cursor=next_cursor, total=total)


@router.get("/profiles/{username}/export")
async def export(username: str, request: Request, filters: Filters, kind: ExportKind = "zip"):
    """Download profile.csv, posts.csv, or a ZIP of both. Filters narrow the posts."""
    record = get_record(request, username)
    content, media_type, filename = build_export(record, kind, filters)
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
