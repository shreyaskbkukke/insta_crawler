"""In-memory store for profiles, posts and collection jobs.

When `data_dir` is set, each profile is snapshotted to `<data_dir>/<username>.json`
after every change, so collections survive restarts and resume from their checkpoint.
"""

import asyncio
import itertools
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from .models import CollectionJob, JobStatus, Post, Profile

log = logging.getLogger(__name__)


class ProfileRecord(BaseModel):
    profile: Profile
    posts: dict[str, Post] = Field(default_factory=dict)
    job: CollectionJob | None = None  # latest collection job
    ever_completed: bool = False

    @property
    def active(self) -> bool:
        return self.job is not None and self.job.status in (JobStatus.QUEUED, JobStatus.RUNNING)


class Store:
    def __init__(self, data_dir: Path | None = None):
        self.data_dir = data_dir
        self.records: dict[str, ProfileRecord] = {}
        self._job_ids = itertools.count(1)

    def load(self) -> None:
        if not self.data_dir or not self.data_dir.exists():
            return
        for path in sorted(self.data_dir.glob("*.json")):
            try:
                record = ProfileRecord.model_validate_json(path.read_text())
            except ValueError:
                log.exception("Skipping unreadable snapshot %s", path)
                continue
            self.records[record.profile.username] = record
        max_id = max((r.job.id for r in self.records.values() if r.job), default=0)
        self._job_ids = itertools.count(max_id + 1)

    def get(self, username: str) -> ProfileRecord | None:
        return self.records.get(username)

    def find_job(self, job_id: int) -> ProfileRecord | None:
        return next((r for r in self.records.values() if r.job and r.job.id == job_id), None)

    def new_job(self) -> CollectionJob:
        return CollectionJob(id=next(self._job_ids))

    async def upsert_profile(self, profile: Profile) -> ProfileRecord:
        # A renamed account keeps its posts: find it by id and re-key it.
        record = next((r for r in self.records.values() if r.profile.id == profile.id), None)
        if record and record.profile.username != profile.username:
            old = record.profile.username
            del self.records[old]
            if self.data_dir:
                (self.data_dir / f"{old}.json").unlink(missing_ok=True)
        if record:
            record.profile = profile
        else:
            record = ProfileRecord(profile=profile)
        self.records[profile.username] = record
        await self.save(record)
        return record

    async def save(self, record: ProfileRecord) -> None:
        if not self.data_dir:
            return
        # Serialize on the event loop (consistent snapshot), write off it.
        payload = record.model_dump_json()
        path = self.data_dir / f"{record.profile.username}.json"
        await asyncio.to_thread(_atomic_write, path, payload)


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(payload)
    tmp.replace(path)
