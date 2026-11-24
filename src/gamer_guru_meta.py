"""Publish one approved Gamer Guru Short natively to Facebook and Instagram.

The workflow invokes this module with a public HTTPS MP4 URL.  It intentionally
does not download from YouTube: a YouTube watch/Short URL is not a reliable
direct media source for Meta's Reels APIs, and using the original master avoids
unnecessary re-encoding.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "state" / "gamer_guru_meta_history.json"
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v27.0").strip()
GRAPH_ROOT = f"https://graph.facebook.com/{GRAPH_VERSION}"


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required GitHub Actions setting: {name}")
    return value


def graph(method: str, path: str, token: str, *, data: dict | None = None, params: dict | None = None) -> dict:
    """Call Graph API without putting an access token into URLs or log output."""
    response = requests.request(
        method,
        f"{GRAPH_ROOT}/{path.lstrip('/')}",
        data={**(data or {}), "access_token": token} if method.upper() == "POST" else None,
        params={**(params or {}), "access_token": token} if method.upper() == "GET" else None,
        timeout=120,
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Meta returned HTTP {response.status_code}") from exc
    if not response.ok or "error" in payload:
        error = payload.get("error") or {}
        raise RuntimeError(f"Meta rejected the request ({error.get('code', response.status_code)}): {error.get('message', 'unknown error')}")
    return payload


def validate_video_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("video_url must be a public HTTPS URL to a direct MP4 file")
    host = parsed.hostname or ""
    if host == "youtu.be" or host.endswith("youtube.com"):
        raise ValueError("Use the original public MP4 URL, not a YouTube watch or Short URL")
    return value


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"posts": {}}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gamer Guru Meta history is not valid JSON") from exc
    if not isinstance(value, dict) or not isinstance(value.get("posts", {}), dict):
        raise RuntimeError("Gamer Guru Meta history has an unexpected format")
    return value


def checkpoint(state: dict, message: str) -> None:
    """Persist each destination independently, preventing a retry from reposting it."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    subprocess.run(["git", "add", str(STATE_PATH.relative_to(ROOT))], cwd=ROOT, check=True)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode
    if not changed:
        return
    subprocess.run(["git", "-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com", "commit", "-m", message], cwd=ROOT, check=True)
    # Other channel workflows can commit while this run is active. This state
    # file is independent, so rebasing is safe and avoids overwriting their work.
    subprocess.run(["git", "pull", "--rebase", "origin", "main"], cwd=ROOT, check=True)
    subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=ROOT, check=True)


def check_access(page_id: str, page_token: str, ig_id: str, ig_token: str) -> None:
    page = graph("GET", page_id, page_token, params={"fields": "id,name"})
    if str(page.get("id")) != page_id:
        raise RuntimeError("Facebook Page token does not match the configured Gamer Guru Page")
    account = graph("GET", ig_id, ig_token, params={"fields": "id,username"})
    if str(account.get("id")) != ig_id:
        raise RuntimeError("Instagram token does not match the configured Gamer Guru account")
    if account.get("username", "").lower() != "gamerguru312":
        raise RuntimeError("Instagram token is not connected to @gamerguru312")
    print(f"Verified Meta access for {page.get('name', 'the configured Facebook Page')} and @{account['username']}.")


def upload_facebook_reel(page_id: str, page_token: str, video_url: str, title: str, caption: str) -> str:
    """Use Meta's three-phase Page Reels API rather than making an ordinary video post."""
    start = graph("POST", f"{page_id}/video_reels", page_token, data={"upload_phase": "start"})
    video_id = start.get("video_id")
    upload_url = start.get("upload_url")
    if not video_id or not upload_url:
        raise RuntimeError("Meta did not return a Facebook Reel upload session")

    upload = requests.post(
        upload_url,
        data={"file_url": video_url},
        headers={"Authorization": f"OAuth {page_token}"},
        timeout=180,
    )
    try:
        upload_payload = upload.json()
    except ValueError as exc:
        raise RuntimeError(f"Meta rejected the Facebook Reel media upload (HTTP {upload.status_code})") from exc
    if not upload.ok or not upload_payload.get("success"):
        detail = upload_payload.get("error") or upload_payload
        raise RuntimeError(f"Meta could not ingest the Facebook Reel source video: {str(detail)[:600]}")

    for _ in range(36):
        status = graph("GET", video_id, page_token, params={"fields": "status"}).get("status") or {}
        phase = status.get("processing_phase") or {}
        if phase.get("status") == "complete":
            break
        if phase.get("status") == "error" or status.get("video_status") == "error":
            error = phase.get("error") or {}
            raise RuntimeError(f"Facebook Reel processing failed: {error.get('message', 'unknown error')}")
        time.sleep(10)
    else:
        raise RuntimeError("Facebook Reel did not finish processing before the safety timeout")

    finished = graph(
        "POST",
        f"{page_id}/video_reels",
        page_token,
        data={
            "upload_phase": "finish",
            "video_id": video_id,
            "video_state": "PUBLISHED",
            "title": title[:255],
            "description": caption,
        },
    )
    if not finished.get("success"):
        raise RuntimeError("Meta did not confirm publication of the Facebook Reel")
    return str(video_id)


def upload_instagram_reel(ig_id: str, ig_token: str, video_url: str, caption: str) -> str:
    container = graph(
        "POST",
        f"{ig_id}/media",
        ig_token,
        data={"media_type": "REELS", "video_url": video_url, "caption": caption[:2200], "share_to_feed": "true"},
    )
    creation_id = container.get("id")
    if not creation_id:
        raise RuntimeError("Meta did not return an Instagram Reel container")
    for _ in range(36):
        status = graph("GET", str(creation_id), ig_token, params={"fields": "status_code"}).get("status_code")
        if status == "FINISHED":
            break
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram Reel processing failed: {status}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram Reel did not finish processing before the safety timeout")
    return str(graph("POST", f"{ig_id}/media_publish", ig_token, data={"creation_id": creation_id})["id"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video-url", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--caption", required=True)
    parser.add_argument("--youtube-url", default="")
    parser.add_argument("--post-key", default="")
    parser.add_argument("--instagram-already-published-url", default="", help="Existing Instagram Reel URL; skip Instagram publishing to avoid a duplicate.")
    parser.add_argument("--publish", action="store_true", help="Create public Meta Reels. Without this flag, only credentials are checked.")
    args = parser.parse_args()

    video_url = validate_video_url(args.video_url)
    title = args.title.strip()
    caption = args.caption.strip()
    if not title or not caption:
        raise ValueError("title and caption cannot be empty")
    if args.youtube_url:
        caption = f"{caption}\n\nWatch the original YouTube Short: {args.youtube_url.strip()}"
    if len(caption) > 2_200:
        raise ValueError("caption is longer than Instagram's 2,200-character limit")

    page_id = require("GAMER_GURU_META_PAGE_ID")
    page_token = require("GAMER_GURU_META_PAGE_TOKEN")
    ig_id = require("GAMER_GURU_META_IG_USER_ID")
    ig_token = require("GAMER_GURU_META_IG_TOKEN")
    check_access(page_id, page_token, ig_id, ig_token)
    if not args.publish:
        print("Validation only: no Reel was published.")
        return

    state = load_state()
    post_key = args.post_key.strip() or hashlib.sha256(video_url.encode("utf-8")).hexdigest()[:20]
    post = state.setdefault("posts", {}).setdefault(
        post_key,
        {"video_url": video_url, "title": title, "created_at": datetime.now(UTC).isoformat()},
    )
    if post.get("video_url") != video_url:
        raise RuntimeError("post_key already belongs to a different source video")
    if not post.get("facebook_reel_id"):
        post["facebook_reel_id"] = upload_facebook_reel(page_id, page_token, video_url, title, caption)
        checkpoint(state, f"Record Gamer Guru Facebook Reel {post_key}")
    else:
        print("Facebook Reel was already recorded; skipping it.")
    if not post.get("instagram_reel_id"):
        existing_instagram_url = args.instagram_already_published_url.strip()
        if existing_instagram_url:
            parsed_instagram = urlparse(existing_instagram_url)
            if parsed_instagram.scheme != "https" or not (parsed_instagram.hostname or "").endswith("instagram.com"):
                raise ValueError("instagram_already_published_url must be an HTTPS Instagram Reel URL")
            post["instagram_reel_id"] = f"preexisting:{existing_instagram_url}"
            post["instagram_reel_url"] = existing_instagram_url
            checkpoint(state, f"Record existing Gamer Guru Instagram Reel {post_key}")
            print("Instagram Reel was already published and recorded; skipping it.")
        else:
            post["instagram_reel_id"] = upload_instagram_reel(ig_id, ig_token, video_url, caption)
            checkpoint(state, f"Record Gamer Guru Instagram Reel {post_key}")
    else:
        print("Instagram Reel was already recorded; skipping it.")
    print("Published Gamer Guru native Reels to Facebook and Instagram.")


if __name__ == "__main__":
    main()
