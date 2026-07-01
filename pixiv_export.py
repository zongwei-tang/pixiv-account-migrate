import time
import json, os
import random
from typing import Callable, cast
from pixivpy3 import AppPixivAPI
from dotenv import load_dotenv

load_dotenv()
OLD_REFRESH_TOKEN = os.getenv("OLD_REFRESH_TOKEN")
assert OLD_REFRESH_TOKEN, "OLD_REFRESH_TOKEN not set in .env"

DELAY_MIN       = 10
DELAY_MAX       = 20
BACKUP_FILE     = "pixiv_backup.json"
CHECKPOINT_FILE = "export_checkpoint.json"
RESTRICTS       = ["public", "private"]
RETRY_WAIT      = 60
RETRY_MAX       = 5


def sleep_random():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def load_checkpoint() -> dict:
    try:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_checkpoint(checkpoint: dict) -> None:
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def check_response(result, label: str) -> bool:
    if result is None:
        print(f"  {label}: response is empty")
        return False
    if hasattr(result, "error") and result.error:
        print(f"  {label}: API returned error - {result.error}")
        return False
    return True


def fetch_page_with_retry(fn, *args, data_key: str, reauth: Callable | None = None, **kwargs):
    for attempt in range(1, RETRY_MAX + 1):
        try:
            page = fn(*args, **kwargs)
        except Exception as e:
            if attempt == RETRY_MAX:
                raise RuntimeError(f"Tried {RETRY_MAX} times, requests failed: {e}")
            print(f"  Network error (attempt {attempt}), retry in {RETRY_WAIT} seconds: {e}")
            time.sleep(RETRY_WAIT)
            if reauth:
                print("  Re-authenticating...")
                reauth()
            continue
        if page and getattr(page, data_key, None) is not None:
            return page
        if attempt < RETRY_MAX:
            print(f"  Empty response (attempt {attempt}), retrying in {RETRY_WAIT} seconds...")
            time.sleep(RETRY_WAIT)
            if reauth:
                print("  Re-authenticating...")
                reauth()
    raise RuntimeError(f"Tried {RETRY_MAX} times, only got empty responses.")


def export_following(api: AppPixivAPI, user_id: int, checkpoint: dict, refresh_token: str) -> list[dict]:
    sec = checkpoint.setdefault("following", {})
    if sec.get("done"):
        print(f"  Following: {len(sec['data'])} (already exported, skipping)")
        return sec["data"]

    result_list     = list(sec.get("data", []))
    resume_restrict = sec.get("restrict", "public")
    resume_url      = sec.get("next_url")
    reauth          = lambda: api.auth(refresh_token=refresh_token)

    for restrict in RESTRICTS:
        if RESTRICTS.index(restrict) < RESTRICTS.index(resume_restrict):
            continue

        if restrict == resume_restrict and resume_url:
            print(f"  Resuming {restrict} following (from checkpoint, {len(result_list)} already fetched)...")
            params = cast(dict[str, str], api.parse_qs(resume_url))
            page = fetch_page_with_retry(api.user_following, data_key="user_previews", reauth=reauth, **params)
        else:
            print(f"  Fetching {restrict} following list...")
            page = fetch_page_with_retry(api.user_following, user_id=user_id, restrict=restrict, data_key="user_previews", reauth=reauth)

        while True:
            for preview in page.user_previews:
                result_list.append({"user_id": preview.user.id, "name": preview.user.name, "restrict": restrict})
            sec.update({"done": False, "data": result_list, "restrict": restrict, "next_url": page.next_url})
            save_checkpoint(checkpoint)
            if not page.next_url:
                break
            sleep_random()
            params = cast(dict[str, str], api.parse_qs(page.next_url))
            page = fetch_page_with_retry(api.user_following, data_key="user_previews", reauth=reauth, **params)

    sec.update({"done": True, "data": result_list, "restrict": None, "next_url": None})
    save_checkpoint(checkpoint)
    print(f"  Following: {len(result_list)}")
    return result_list


def export_illust_bookmarks(api: AppPixivAPI, user_id: int, checkpoint: dict, refresh_token: str) -> list[dict]:
    sec = checkpoint.setdefault("illust_bookmarks", {})
    if sec.get("done"):
        print(f"  Illust bookmarks: {len(sec['data'])} (already exported, skipping)")
        return sec["data"]

    result_list     = list(sec.get("data", []))
    resume_restrict = sec.get("restrict", "public")
    resume_url      = sec.get("next_url")
    reauth          = lambda: api.auth(refresh_token=refresh_token)

    for restrict in RESTRICTS:
        if RESTRICTS.index(restrict) < RESTRICTS.index(resume_restrict):
            continue

        if restrict == resume_restrict and resume_url:
            print(f"  Resuming illust {restrict} bookmarks (from checkpoint, {len(result_list)} already fetched)...")
            params = cast(dict[str, str], api.parse_qs(resume_url))
            page = fetch_page_with_retry(api.user_bookmarks_illust, data_key="illusts", reauth=reauth, **params)
        else:
            print(f"  Fetching illust {restrict} bookmarks...")
            page = fetch_page_with_retry(api.user_bookmarks_illust, user_id=user_id, restrict=restrict, data_key="illusts", reauth=reauth)

        while True:
            for illust in page.illusts:
                result_list.append({"illust_id": illust.id, "title": illust.title, "restrict": restrict})
            sec.update({"done": False, "data": result_list, "restrict": restrict, "next_url": page.next_url})
            save_checkpoint(checkpoint)
            if not page.next_url:
                break
            sleep_random()
            params = cast(dict[str, str], api.parse_qs(page.next_url))
            page = fetch_page_with_retry(api.user_bookmarks_illust, data_key="illusts", reauth=reauth, **params)

    sec.update({"done": True, "data": result_list, "restrict": None, "next_url": None})
    save_checkpoint(checkpoint)
    print(f"  Illust bookmarks: {len(result_list)}")
    return result_list


def export_novel_bookmarks(api: AppPixivAPI, user_id: int, checkpoint: dict, refresh_token: str) -> list[dict]:
    sec = checkpoint.setdefault("novel_bookmarks", {})
    if sec.get("done"):
        print(f"  Novel bookmarks: {len(sec['data'])} (already exported, skipping)")
        return sec["data"]

    result_list     = list(sec.get("data", []))
    resume_restrict = sec.get("restrict", "public")
    resume_url      = sec.get("next_url")
    reauth          = lambda: api.auth(refresh_token=refresh_token)

    for restrict in RESTRICTS:
        if RESTRICTS.index(restrict) < RESTRICTS.index(resume_restrict):
            continue

        if restrict == resume_restrict and resume_url:
            print(f"  Resuming novel {restrict} bookmarks (from checkpoint, {len(result_list)} already fetched)...")
            params = cast(dict[str, str], api.parse_qs(resume_url))
            page = fetch_page_with_retry(api.user_bookmarks_novel, data_key="novels", reauth=reauth, **params)
        else:
            print(f"  Fetching novel {restrict} bookmarks...")
            page = fetch_page_with_retry(api.user_bookmarks_novel, user_id=user_id, restrict=restrict, data_key="novels", reauth=reauth)

        while True:
            for novel in page.novels:
                result_list.append({"novel_id": novel.id, "title": novel.title, "restrict": restrict})
            sec.update({"done": False, "data": result_list, "restrict": restrict, "next_url": page.next_url})
            save_checkpoint(checkpoint)
            if not page.next_url:
                break
            sleep_random()
            params = cast(dict[str, str], api.parse_qs(page.next_url))
            page = fetch_page_with_retry(api.user_bookmarks_novel, data_key="novels", reauth=reauth, **params)

    sec.update({"done": True, "data": result_list, "restrict": None, "next_url": None})
    save_checkpoint(checkpoint)
    print(f"  Novel bookmarks: {len(result_list)}")
    return result_list


def main():
    print("=" * 55)
    print("  STEP 1 / 2  Log in to old account")
    print("=" * 55)
    old_api = AppPixivAPI()
    old_api.auth(refresh_token=OLD_REFRESH_TOKEN)
    old_user_id = int(old_api.user_id)
    print(f"  Old account user_id: {old_user_id}\n")

    checkpoint = load_checkpoint()
    if checkpoint:
        done_sections = [k for k, v in checkpoint.items() if v.get("done")]
        print(f"  Found checkpoint, already done: {done_sections or 'none'}\n")

    print("=" * 55)
    print("  STEP 2 / 2  Export data from old account")
    print("=" * 55)
    following        = export_following(old_api, old_user_id, checkpoint, OLD_REFRESH_TOKEN)
    illust_bookmarks = export_illust_bookmarks(old_api, old_user_id, checkpoint, OLD_REFRESH_TOKEN)
    novel_bookmarks  = export_novel_bookmarks(old_api, old_user_id, checkpoint, OLD_REFRESH_TOKEN)

    backup = {
        "following":        following,
        "illust_bookmarks": illust_bookmarks,
        "novel_bookmarks":  novel_bookmarks,
    }
    with open(BACKUP_FILE, "w", encoding="utf-8") as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"""
  Backup saved to {BACKUP_FILE}
     Following:        {len(following)}
     Illust bookmarks: {len(illust_bookmarks)}
     Novel bookmarks:  {len(novel_bookmarks)}
  Export complete. Run pixiv_import.py to import to new account.
    """)


if __name__ == "__main__":
    main()
