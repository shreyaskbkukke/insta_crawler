import httpx
import pytest

from insta_crawler.app import create_app
from insta_crawler.config import Settings

from fakes import FakeDataSource


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path / "data",
        collection_page_delay_seconds=0,
        collection_retry_base_seconds=0,
        collection_max_retries=0,
    )


@pytest.fixture
def source():
    return FakeDataSource(page_size=10, delay=0)


@pytest.fixture
async def app(settings, source):
    app = create_app(settings, source)
    async with app.router.lifespan_context(app):
        yield app


@pytest.fixture
async def client(app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def collect(app, client, username: str) -> dict:
    resp = await client.post("/api/collections", json={"username": username})
    assert resp.status_code == 202, resp.text
    job = resp.json()
    await app.state.collector.wait(job["id"])
    return (await client.get(f"/api/collections/{job['id']}")).json()
