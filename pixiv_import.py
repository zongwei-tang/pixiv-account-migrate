import sys
import time
import json
import os
import random
from pixivpy3 import AppPixivAPI
from dotenv import load_dotenv

load_dotenv()
NEW_REFRESH_TOKEN = os.getenv("NEW_REFRESH_TOKEN")
assert NEW_REFRESH_TOKEN, "NEW_REFRESH_TOKEN not set in .env"

DELAY_MIN       = 10
DELAY_MAX       = 20
CHECKPOINT_FILE = "import_checkpoint.json"
REAUTH_WAIT     = 30


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


def is_oauth_error(result) -> bool:
    if result is None:
        return False
    if hasattr(result, "error") and result.error:
        msg = str(result.error)
        return "invalid_grant" in msg or "OAuth" in msg
    return False


def check_response(result, label: str) -> bool:
    if result is None:
        print(f"  {label}: response is empty")
        return False
    if hasattr(result, "error") and result.error:
        print(f"  {label}: API returned error - {result.error}")
        return False
    return True


def call_with_reauth(api: AppPixivAPI, fn, label: str, **kwargs):
    result = fn(**kwargs)
    if is_oauth_error(result):
        print(f"  Token expired, re-authenticating and retrying {label}...")
        api.auth(refresh_token=NEW_REFRESH_TOKEN)
        time.sleep(REAUTH_WAIT)
        result = fn(**kwargs)
    return result


def novel_bookmark_add(api: AppPixivAPI, novel_id: int, restrict: str = "public"):
    url = f"{api.hosts}/v2/novel/bookmark/add"
    data = {"novel_id": novel_id, "restrict": restrict}
    r = api.no_auth_requests_call("POST", url, data=data, req_auth=True)
    return api.parse_result(r)


def reimport_following(api: AppPixivAPI, following: list[dict], checkpoint: dict) -> None:
    sec = checkpoint.setdefault("following", {})
    if sec.get("done"):
        print("  Following: already imported, skipping")
        return

    start  = sec.get("offset", 0)
    total  = len(following)
    failed = list(sec.get("failed", []))
    silent_fail_count = 0

    if start > 0:
        print(f"  Resuming from checkpoint: following ({start}/{total} already processed)")
    print(f"  Importing {total - start} following entries, {DELAY_MIN}-{DELAY_MAX} seconds between each...")

    for i, entry in enumerate(following[start:], start=start + 1):
        uid, name, restrict = entry["user_id"], entry["name"], entry["restrict"]
        try:
            result = call_with_reauth(
                api, api.user_follow_add,
                label=name, user_id=uid, restrict=restrict
            )
            if check_response(result, f"follow {name}"):
                print(f"  [{i:>4}/{total}] OK {name} (uid={uid}, {restrict})")
            else:
                silent_fail_count += 1
                failed.append(entry)
        except Exception as e:
            print(f"  [{i:>4}/{total}] FAIL {name} (uid={uid}): {e}")
            failed.append(entry)

        sec.update({"done": False, "offset": i, "failed": failed})
        save_checkpoint(checkpoint)
        sleep_random()

    sec.update({"done": True, "offset": total, "failed": failed})
    save_checkpoint(checkpoint)

    print(f"\n  Following import complete: {total - len(failed)} / {total} succeeded")
    if silent_fail_count:
        print(f"  Silent failures: {silent_fail_count}")
    if failed:
        with open("failed_following.json", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print("  Failed entries saved to failed_following.json")


def reimport_illust_bookmarks(api: AppPixivAPI, bookmarks: list[dict], checkpoint: dict) -> None:
    sec = checkpoint.setdefault("illust_bookmarks", {})
    if sec.get("done"):
        print("  Illust bookmarks: already imported, skipping")
        return

    start  = sec.get("offset", 0)
    total  = len(bookmarks)
    failed = list(sec.get("failed", []))
    silent_fail_count = 0

    if start > 0:
        print(f"  Resuming from checkpoint: illust bookmarks ({start}/{total} already processed)")
    print(f"  Importing {total - start} illust bookmarks, {DELAY_MIN}-{DELAY_MAX} seconds between each...")

    for i, entry in enumerate(bookmarks[start:], start=start + 1):
        iid, title, restrict = entry["illust_id"], entry["title"], entry["restrict"]
        try:
            result = call_with_reauth(
                api, api.illust_bookmark_add,
                label=title, illust_id=iid, restrict=restrict
            )
            if check_response(result, f"illust {iid}"):
                print(f"  [{i:>4}/{total}] OK {title} (id={iid}, {restrict})")
            else:
                silent_fail_count += 1
                failed.append(entry)
        except Exception as e:
            print(f"  [{i:>4}/{total}] FAIL {title} (id={iid}): {e}")
            failed.append(entry)

        sec.update({"done": False, "offset": i, "failed": failed})
        save_checkpoint(checkpoint)
        sleep_random()

    sec.update({"done": True, "offset": total, "failed": failed})
    save_checkpoint(checkpoint)

    print(f"\n  Illust bookmarks import complete: {total - len(failed)} / {total} succeeded")
    if silent_fail_count:
        print(f"  Silent failures: {silent_fail_count}")
    if failed:
        with open("failed_illust_bookmarks.json", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print("  Failed entries saved to failed_illust_bookmarks.json")


def reimport_novel_bookmarks(api: AppPixivAPI, bookmarks: list[dict], checkpoint: dict) -> None:
    sec = checkpoint.setdefault("novel_bookmarks", {})
    if sec.get("done"):
        print("  Novel bookmarks: already imported, skipping")
        return

    start  = sec.get("offset", 0)
    total  = len(bookmarks)
    failed = list(sec.get("failed", []))
    silent_fail_count = 0

    if start > 0:
        print(f"  Resuming from checkpoint: novel bookmarks ({start}/{total} already processed)")
    print(f"  Importing {total - start} novel bookmarks, {DELAY_MIN}-{DELAY_MAX} seconds between each...")

    for i, entry in enumerate(bookmarks[start:], start=start + 1):
        nid, title, restrict = entry["novel_id"], entry["title"], entry["restrict"]
        try:
            result = call_with_reauth(
                api, lambda **kw: novel_bookmark_add(api, **kw),
                label=title, novel_id=nid, restrict=restrict
            )
            if check_response(result, f"novel {nid}"):
                print(f"  [{i:>4}/{total}] OK {title} (id={nid}, {restrict})")
            else:
                silent_fail_count += 1
                failed.append(entry)
        except Exception as e:
            print(f"  [{i:>4}/{total}] FAIL {title} (id={nid}): {e}")
            failed.append(entry)

        sec.update({"done": False, "offset": i, "failed": failed})
        save_checkpoint(checkpoint)
        sleep_random()

    sec.update({"done": True, "offset": total, "failed": failed})
    save_checkpoint(checkpoint)

    print(f"\n  Novel bookmarks import complete: {total - len(failed)} / {total} succeeded")
    if silent_fail_count:
        print(f"  Silent failures: {silent_fail_count}")
    if failed:
        with open("failed_novel_bookmarks.json", "w", encoding="utf-8") as f:
            json.dump(failed, f, ensure_ascii=False, indent=2)
        print("  Failed entries saved to failed_novel_bookmarks.json")


def load_json_if_exists(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def main():
    retry_mode = "--retry" in sys.argv

    print("=" * 55)
    if retry_mode:
        print("  Mode: retry failed entries (reading failed_*.json)")
        print("=" * 55)
        following        = load_json_if_exists("failed_following.json")
        illust_bookmarks = load_json_if_exists("failed_illust_bookmarks.json")
        novel_bookmarks  = load_json_if_exists("failed_novel_bookmarks.json")
        checkpoint       = {}
    else:
        print("  Reading pixiv_backup.json")
        print("=" * 55)
        with open("pixiv_backup.json", "r", encoding="utf-8") as f:
            backup = json.load(f)
        following        = backup.get("following", [])
        illust_bookmarks = backup.get("illust_bookmarks", backup.get("bookmarks", []))
        novel_bookmarks  = backup.get("novel_bookmarks", [])
        checkpoint       = load_checkpoint()
        if checkpoint:
            done    = [k for k, v in checkpoint.items() if v.get("done")]
            offsets = {k: v.get("offset", 0) for k, v in checkpoint.items() if not v.get("done")}
            print("  Found import_checkpoint.json")
            if done:    print(f"    Done: {done}")
            if offsets: print(f"    In progress: {offsets}")
            print()

    print(f"  Following:        {len(following)}")
    print(f"  Illust bookmarks: {len(illust_bookmarks)}")
    print(f"  Novel bookmarks:  {len(novel_bookmarks)}\n")

    est_min = (len(following) + len(illust_bookmarks) + len(novel_bookmarks)) * (DELAY_MIN + DELAY_MAX) / 2 / 60
    print(f"  Estimated total time: {est_min:.0f} min ({est_min/60:.1f} hours)\n")

    print("=" * 55)
    print("  Logging in to new account")
    print("=" * 55)
    api = AppPixivAPI()
    api.auth(refresh_token=NEW_REFRESH_TOKEN)
    print(f"  New account user_id: {api.user_id}\n")

    if following:
        print("=" * 55)
        print(f"  Importing following list ({len(following)})")
        print("=" * 55)
        reimport_following(api, following, checkpoint)

    if illust_bookmarks:
        print("\n" + "=" * 55)
        print(f"  Importing illust bookmarks ({len(illust_bookmarks)})")
        print("=" * 55)
        reimport_illust_bookmarks(api, illust_bookmarks, checkpoint)

    if novel_bookmarks:
        print("\n" + "=" * 55)
        print(f"  Importing novel bookmarks ({len(novel_bookmarks)})")
        print("=" * 55)
        reimport_novel_bookmarks(api, novel_bookmarks, checkpoint)

    if not any([following, illust_bookmarks, novel_bookmarks]):
        print("  Nothing to import, exiting.")
        return

    print("\n" + "=" * 55)
    print("  Import complete!")
    print("=" * 55)
    print("  Refresh Pixiv in a few minutes to check the results.")


if __name__ == "__main__":
    main()
