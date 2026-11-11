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

### Prerequisites

- An Instagram **Business or Creator** account linked to a Facebook Page.
- A Meta Developer account: [developers.facebook.com](https://developers.facebook.com)

### Steps to get `IG_ACCESS_TOKEN` and `IG_USER_ID`

1. **Create a Meta app**
   - Go to [developers.facebook.com/apps](https://developers.facebook.com/apps) and click **Create App**.
   - Choose **Business** as the use case, then follow the prompts.
   - Under **Add Products**, add **Instagram Graph API**.

2. **Generate a User Access Token**
   - Open the **Graph API Explorer**: [developers.facebook.com/tools/explorer](https://developers.facebook.com/tools/explorer/)
   - Select your app from the top-right dropdown.
   - Click **Generate Access Token** and grant the required permissions:
     - `instagram_basic`
     - `instagram_manage_insights` *(optional, for some metadata)*
     - `pages_show_list`
     - `pages_read_engagement`
   - Copy the token shown — this is a **short-lived** token (valid ~1 hour).

3. **Exchange for a long-lived token** (valid ~60 days)

   ```text
   GET https://graph.facebook.com/v23.0/oauth/access_token
     ?grant_type=fb_exchange_token
     &client_id=<APP_ID>
     &client_secret=<APP_SECRET>
     &fb_exchange_token=<SHORT_LIVED_TOKEN>
   ```

   Your app ID and secret are on [developers.facebook.com/apps](https://developers.facebook.com/apps) → your app → **App settings → Basic**.

4. **Find your IG User ID**

   In the Graph API Explorer, run:

   ```text
   GET /me/accounts?fields=instagram_business_account
   ```

   Each page entry has an `instagram_business_account.id` — that is your `IG_USER_ID`.

5. **Set the env vars**

   ```bash
   cp .env.example .env
   # then edit .env:
   IG_ACCESS_TOKEN=<your long-lived token>
   IG_USER_ID=<your instagram_business_account id>
   ```

> **Token expiry:** long-lived tokens expire after ~60 days. Refresh them by repeating step 3 before they expire, or set up a System User token in **Meta Business Suite → Business Settings → System Users** for tokens that don't expire.

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
