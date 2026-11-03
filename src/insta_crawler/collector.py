"""Background collection of a profile's posts, checkpointed so interrupted jobs resume."""

import asyncio
import logging

from .adapters.base import DataSource, DataSourceError, PostPage, RateLimitedError, TransientError
from .config import Settings
from .models import CollectionJob, JobStatus, utcnow
from .store import ProfileRecord, Store

log = logging.getLogger(__name__)


class Collector:
    def __init__(self, store: Store, source: DataSource, settings: Settings):
        self.store = store
        self.source = source
        self.settings = settings
        self._tasks: dict[int, asyncio.Task] = {}

    async def start(self, record: ProfileRecord) -> CollectionJob:
        """Return the active job, resume a failed one from its cursor, or start a fresh one."""
        job = record.job
        if job and job.status is JobStatus.FAILED and not job.reached_end:
            job.status = JobStatus.QUEUED
            job.error = None
        elif not record.active:
            job = record.job = self.store.new_job()
        await self.store.save(record)
        self._spawn(record, job.id)
        return job

    async def resume_incomplete(self) -> None:
        """On startup, pick up jobs that were queued/running when the process stopped."""
        for record in self.store.records.values():
            if record.active:
                log.info("Resuming collection job %s for @%s", record.job.id, record.profile.username)
                self._spawn(record, record.job.id)

    def _spawn(self, record: ProfileRecord, job_id: int) -> None:
        task = self._tasks.get(job_id)
        if task and not task.done():
            return
        task = asyncio.create_task(self._run(record), name=f"collect-{job_id}")
        self._tasks[job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job_id, None))

    async def shutdown(self) -> None:
        tasks = list(self._tasks.values())
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def wait(self, job_id: int) -> None:
        if task := self._tasks.get(job_id):
            await asyncio.gather(task, return_exceptions=True)

    async def _fetch_with_retry(self, username: str, cursor: str | None) -> PostPage:
        attempts = self.settings.collection_max_retries
        for attempt in range(attempts + 1):
            try:
                return await self.source.fetch_posts(username, cursor)
            except TransientError as exc:
                if attempt == attempts:
                    raise
                delay = min(60.0, self.settings.collection_retry_base_seconds * 2**attempt)
                if isinstance(exc, RateLimitedError) and exc.retry_after:
                    delay = exc.retry_after
                log.warning("Transient error (%s); retry %d/%d in %.1fs", exc, attempt + 1, attempts, delay)
                await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    async def _run(self, record: ProfileRecord) -> None:
        job = record.job
        job.status = JobStatus.RUNNING
        job.started_at = job.started_at or utcnow()
        await self.store.save(record)
        try:
            while True:
                page = await self._fetch_with_retry(record.profile.username, job.cursor)
                # Upsert by post id: re-fetched posts replace the old copy, never duplicate.
                for post in page.posts:
                    record.posts[post.id] = post
                job.cursor = page.next_cursor
                job.retrieved_count += len(page.posts)
                if page.next_cursor is None:
                    job.reached_end = True
                    job.status = JobStatus.COMPLETED
                    job.completed_at = utcnow()
                    record.ever_completed = True
                # Posts and checkpoint are saved together, so a crash never skips a page.
                await self.store.save(record)
                if job.reached_end:
                    return
                await asyncio.sleep(self.settings.collection_page_delay_seconds)
        except asyncio.CancelledError:
            # Status stays RUNNING; resume_incomplete() continues from the checkpoint.
            raise
        except Exception as exc:
            if not isinstance(exc, DataSourceError):
                log.exception("Collection job %s crashed", job.id)
            job.status = JobStatus.FAILED
            job.error = str(exc) or exc.__class__.__name__
            job.completed_at = utcnow()
            await self.store.save(record)
