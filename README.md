# pixiv-migrate

Move your following list, illust bookmarks, and novel bookmarks from one Pixiv account to another.

## Setup

```bash
uv sync
```

Create a `.env` file:

```
OLD_REFRESH_TOKEN=...
NEW_REFRESH_TOKEN=...
```

Get a refresh token for each account by running:

```bash
uv run get_token.py
```

It opens a Pixiv login page in your browser, log in with the account you want a token for, then paste the `code=` value from the callback URL back into the terminal.

## Usage

1. Export data from the old account:

   ```bash
   uv run pixiv_export.py
   ```

   This logs into the old account, downloads following/bookmarks, and saves them to `pixiv_backup.json`. If it's interrupted, just rerun it — it resumes from `export_checkpoint.json`.

2. Import into the new account:

   ```bash
   uv run pixiv_import.py
   ```

   This reads `pixiv_backup.json` and imports everything into the new account. If it's interrupted, rerun it — it resumes from `import_checkpoint.json`. Already-imported items are skipped (Pixiv ignores duplicate follows/bookmarks anyway).

3. If some items failed, retry just those:

   ```bash
   uv run pixiv_import.py --retry
   ```

   This reads `failed_following.json` / `failed_illust_bookmarks.json` / `failed_novel_bookmarks.json` and retries only the failed entries.

## Notes

- A delay (10-20s) is used between each API call to avoid rate limiting. For large accounts this can take hours.
