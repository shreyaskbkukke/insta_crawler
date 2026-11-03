# insta-crawler: Instagram profile explorer

Type in an Instagram **Business or Creator** username or profile URL. The app collects the profile's posts, lets you browse them with filters and sorting (oldest or newest first), links each post to Instagram, and exports the data as CSV.

- **Backend:** FastAPI (`src/insta_crawler/`). There is no database. Profiles live in memory, and each one is snapshotted to `data/<username>.json` after every page, so a collection that gets interrupted resumes from its checkpoint without creating duplicates.
- **Frontend:** Next.js (`web/`). It proxies `/api/*` to the backend.

## Run it

```bash
# backend → http://127.0.0.1:8000  (API docs at /docs)
cp .env.example .env           # fill in IG_ACCESS_TOKEN and IG_USER_ID (see below)
uv run insta-crawler

# frontend → http://localhost:3000
cd web && npm install && npm run dev    # API_URL=... if the backend is not on 127.0.0.1:8000
```

Tests: `uv run pytest` (they use a fake data source in `tests/fakes.py`, so they need no credentials)

## Instagram access (Graph API Business Discovery)

The app uses the official Graph API. **Business Discovery** lets *your* Instagram Business/Creator account read public data from other Business/Creator accounts. Personal accounts can't be reached this way.

1. Convert your Instagram account to Business or Creator and link it to a Facebook Page.
2. Create a Meta app with Facebook Login. Generate a user or system-user token that has the Instagram permissions Business Discovery needs (`instagram_basic`, plus Page access). Check Meta's current docs, because the required permissions change.
3. Find your IG user id with `GET /me/accounts?fields=instagram_business_account`.
4. Set `IG_ACCESS_TOKEN` and `IG_USER_ID` in `.env`.

What the Graph API can and can't return:
- **Like counts:** blank when the owner hides likes.
- **View counts:** never available through Business Discovery, so the column stays blank.
- **Media URLs:** Instagram CDN links expire. Collect the profile again to refresh thumbnails.
- **Rate limits:** if collection stops on a rate limit, it's marked "Stopped". Pressing **Resume** continues from the saved cursor.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/collections` `{username}` | Look up the profile and start, resume, or refresh collection |
| GET | `/api/collections/{job_id}` | Job status and progress |
| GET | `/api/profiles/{username}` | Profile, collection summary, and known limitations |
| GET | `/api/profiles/{username}/posts` | `sort=newest\|oldest`, `type`, `from`, `to`, `keyword`, `min_likes`, `min_comments`, `cursor`, `limit` |
| GET | `/api/profiles/{username}/export` | `kind=zip\|posts\|profile`, plus the same filters as `/posts` |

Pagination is keyset-based on `(published_at, id)`. Sorting and filtering apply to the whole collected set, not just the current page.

CSV exports:
- Unavailable values are left blank, never written as 0.
- Text that starts with `= + - @` is escaped so spreadsheets don't run it as a formula.
- `profile.csv` records the collection status, whether the collection is complete, the export scope (all or filtered), and the export time.
