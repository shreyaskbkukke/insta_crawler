import csv
import io
import zipfile

import httpx

from conftest import collect
from insta_crawler.app import create_app


async def test_collect_full_profile(app, client, source):
    job = await collect(app, client, "brand.one")
    assert job["status"] == "completed" and job["reached_end"]

    detail = (await client.get("/api/profiles/brand.one")).json()
    reported = source._post_total("brand.one")
    assert detail["collection"]["complete"] is True
    assert detail["collection"]["posts_collected"] == reported == detail["profile"]["media_count"]
    assert detail["profile"]["profile_url"] == "https://www.instagram.com/brand.one/"


async def test_profile_url_input_and_errors(app, client):
    job = await collect(app, client, "https://www.instagram.com/tiny_shop/")
    assert job["username"] == "tiny_shop"

    assert (await client.post("/api/collections", json={"username": "not valid!"})).status_code == 422
    resp = await client.post("/api/collections", json={"username": "personal_acct"})
    assert resp.status_code == 404
    assert "Business/Creator" in resp.json()["detail"]
    assert (await client.get("/api/profiles/never_seen")).status_code == 404


async def test_interrupted_collection_resumes_without_duplicates(app, client, source):
    source.fail_every = 3  # every 3rd page fails; with no retries the job stops each time
    job = await collect(app, client, "flaky_brand")
    assert job["status"] == "failed"
    first_count = job["retrieved_count"]
    assert first_count > 0

    for _ in range(50):
        job = await collect(app, client, "flaky_brand")
        if job["status"] == "completed":
            break
    assert job["status"] == "completed"

    detail = (await client.get("/api/profiles/flaky_brand")).json()
    assert detail["collection"]["posts_collected"] == source._post_total("flaky_brand")

    # A refresh after completion re-upserts the same posts without duplicating them.
    source.fail_every = 0
    await collect(app, client, "flaky_brand")
    detail = (await client.get("/api/profiles/flaky_brand")).json()
    assert detail["collection"]["posts_collected"] == source._post_total("flaky_brand")


async def all_pages(client, username, **params):
    items, cursor = [], None
    while True:
        q = {**params, "limit": 7, **({"cursor": cursor} if cursor else {})}
        page = (await client.get(f"/api/profiles/{username}/posts", params=q)).json()
        items += page["items"]
        cursor = page["next_cursor"]
        if not cursor:
            return items, page["total"]


async def test_pagination_is_globally_sorted_and_complete(app, client, source):
    await collect(app, client, "brand.two")
    total = source._post_total("brand.two")

    for sort in ("newest", "oldest"):
        items, reported_total = await all_pages(client, "brand.two", sort=sort)
        keys = [(p["published_at"], p["id"]) for p in items]
        assert reported_total == total == len(items) == len(set(keys))
        assert keys == sorted(keys, reverse=sort == "newest")


async def test_filters(app, client):
    await collect(app, client, "brand.three")
    reels, total = await all_pages(client, "brand.three", type="reel")
    assert reels and all(p["post_type"] == "reel" for p in reels) and len(reels) == total

    items, _ = await all_pages(client, "brand.three", **{"from": "2025-01-01", "to": "2025-06-30"})
    assert items and all("2025-01-01" <= p["published_at"][:10] <= "2025-06-30" for p in items)

    items, _ = await all_pages(client, "brand.three", keyword="COFFEE")
    assert items and all("coffee" in (p["caption"] or "").lower() for p in items)

    items, _ = await all_pages(client, "brand.three", min_likes=40000)
    assert items and all(p["like_count"] is not None and p["like_count"] >= 40000 for p in items)

    assert (await client.get("/api/profiles/brand.three/posts", params={"cursor": "junk"})).status_code == 400


def read_csv(data: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


async def test_exports_match_stored_results(app, client, source):
    await collect(app, client, "brand.four")
    resp = await client.get("/api/profiles/brand.four/export", params={"kind": "zip"})
    assert resp.status_code == 200 and resp.headers["content-type"] == "application/zip"
    assert "attachment" in resp.headers["content-disposition"]
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        profile = read_csv(zf.read("profile.csv"))
        posts = read_csv(zf.read("posts.csv"))
    assert len(profile) == 1 and profile[0]["collection_complete"] == "true"
    assert profile[0]["export_scope"] == "all"
    assert len(posts) == source._post_total("brand.four") == int(profile[0]["posts_in_export"])
    # Hidden like counts stay blank instead of becoming zero.
    assert any(p["like_count"] == "" for p in posts)
    assert all(p["post_url"].startswith("https://www.instagram.com/p/") for p in posts)

    params = {"kind": "posts", "type": "carousel", "sort": "oldest"}
    rows = read_csv((await client.get("/api/profiles/brand.four/export", params=params)).content)
    _, expected = await all_pages(client, "brand.four", type="carousel")
    assert len(rows) == expected
    assert all(r["post_type"] == "carousel" and int(r["media_count"]) >= 2 for r in rows)
    assert [r["published_at"] for r in rows] == sorted(r["published_at"] for r in rows)


async def test_restart_resumes_from_snapshot(settings, source):
    source.fail_every = 2
    first = create_app(settings, source)
    async with first.router.lifespan_context(first):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=first), base_url="http://t") as c:
            job = await collect(first, c, "restart_brand")
    assert job["status"] == "failed" and job["retrieved_count"] == 10

    source.fail_every = 0
    second = create_app(settings, source)
    async with second.router.lifespan_context(second):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=second), base_url="http://t") as c:
            detail = (await c.get("/api/profiles/restart_brand")).json()
            assert detail["collection"]["posts_collected"] == 10  # loaded from the JSON snapshot
            job = await collect(second, c, "restart_brand")
            assert job["id"] == detail["collection"]["job"]["id"]  # same job, resumed from cursor
            assert job["status"] == "completed"
            detail = (await c.get("/api/profiles/restart_brand")).json()
            assert detail["collection"]["posts_collected"] == source._post_total("restart_brand")
