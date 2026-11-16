"""Publish rendered Unlearn The Fear videos with idempotent checkpoints."""
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import requests

from video_pipeline import DOCS, ROOT, load_state, save_state


def graph(method: str, path: str, *, params: dict | None = None, files=None):
    version = os.getenv("META_GRAPH_VERSION", "v27.0").strip()
    host = "https://graph-video.facebook.com" if files else "https://graph.facebook.com"
    response = requests.request(method, f"{host}/{version}/{path}", data=params if method == "POST" else None, params=params if method == "GET" else None, files=files, timeout=240)
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"Meta returned HTTP {response.status_code}") from exc
    if not response.ok or "error" in data:
        error = data.get("error", {})
        raise RuntimeError(f"Meta error {error.get('code')}: {error.get('message', 'unknown error')}")
    return data


def checkpoint(message: str, state: dict) -> None:
    save_state(state)
    subprocess.run(["git", "add", "state/video_state.json"], cwd=ROOT, check=True)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if changed.returncode:
        subprocess.run(["git", "-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com", "commit", "-m", message], cwd=ROOT, check=True)
        subprocess.run(["git", "push"], cwd=ROOT, check=True)


def check_public(url: str, expected_prefix: str) -> None:
    for _ in range(18):
        try:
            response = requests.get(url, stream=True, timeout=20, headers={"Cache-Control": "no-cache"})
            if response.ok and response.headers.get("Content-Type", "").lower().startswith(expected_prefix):
                return
        except requests.RequestException:
            pass
        time.sleep(8)
    raise RuntimeError(f"Rendered MP4 is not publicly reachable yet: {url}")


def caption_with_visual_credits(post: dict) -> str:
    credits = post.get("visual_credits") or []
    if not credits:
        return post["caption"]
    lines = ["Visual credits:"]
    for credit in credits:
        lines.append(f"{credit['title']} — {credit['creator']} ({credit['license']}): {credit['source']}")
    caption = post["caption"] + "\n\n" + "\n".join(lines)
    if len(caption) > 2_200:
        # Instagram has the shortest caption limit. Keep the core caption and
        # enough credits to preserve attribution without causing a failed post.
        return post["caption"] + "\n\nVisual credits: Wikimedia Commons; full source record retained in the automation state."
    return caption


def upload_youtube(video: Path, post: dict, *, unlisted: bool) -> str:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:
        raise RuntimeError("YouTube dependencies are missing from requirements.txt") from exc
    raw = os.getenv("YOUTUBE_TOKEN_JSON_B64", "").strip()
    if not raw:
        raise RuntimeError("Missing YOUTUBE_TOKEN_JSON_B64 GitHub secret. Complete the one-time YouTube OAuth connection first.")
    token = json.loads(base64.b64decode(raw))
    credentials = Credentials.from_authorized_user_info(token, ["https://www.googleapis.com/auth/youtube.upload"])
    if not credentials.valid:
        credentials.refresh(Request())
    client = build("youtube", "v3", credentials=credentials, cache_discovery=False)
    request = client.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": post["title"][:100], "description": caption_with_visual_credits(post), "tags": ["Unlearn The Fear", "motivation", "mindfulness", "personal growth"], "categoryId": "27"},
            "status": {"privacyStatus": "unlisted" if unlisted else "public", "selfDeclaredMadeForKids": False},
        },
        media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True, chunksize=8 * 1024 * 1024),
        notifySubscribers=False,
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    return response["id"]


def publish_instagram(post: dict, video_url: str, token: str, ig_id: str) -> str:
    container = graph("POST", f"{ig_id}/media", params={"media_type": "REELS", "video_url": video_url, "caption": caption_with_visual_credits(post), "share_to_feed": "true", "access_token": token})
    for _ in range(30):
        status = graph("GET", container["id"], params={"fields": "status_code", "access_token": token}).get("status_code")
        if status == "FINISHED":
            return graph("POST", f"{ig_id}/media_publish", params={"creation_id": container["id"], "access_token": token})["id"]
        if status in {"ERROR", "EXPIRED"}:
            raise RuntimeError(f"Instagram Reel processing failed: {status}")
        time.sleep(10)
    raise RuntimeError("Instagram Reel was not ready before the safety timeout")


def publish_facebook(post: dict, video: Path, token: str, page_id: str) -> str:
    with video.open("rb") as handle:
        response = graph("POST", f"{page_id}/videos", files={"source": (video.name, handle, "video/mp4")}, params={"title": post["title"], "description": caption_with_visual_credits(post), "published": "true", "access_token": token})
    return response.get("post_id") or response["id"]


def publish(kind: str, *, youtube_unlisted: bool) -> None:
    state = load_state()
    key = f"pending_{kind}"
    post = state.get(key)
    if not post:
        print("Nothing pending.")
        return
    page_id = os.getenv("META_PAGE_ID", "").strip()
    page_token = os.getenv("META_PAGE_TOKEN", "").strip()
    ig_id = os.getenv("META_IG_USER_ID", "").strip()
    ig_token = os.getenv("META_IG_TOKEN", "").strip()
    if not all((page_id, page_token, ig_id, ig_token)):
        raise RuntimeError("Missing Meta account variables or tokens")
    video = DOCS / post["video_path"]
    if not video.exists():
        raise RuntimeError("Rendered video is missing; re-run the renderer before publishing")
    base = os.getenv("PAGES_BASE_URL", "").strip()
    if not base.startswith("https://") or not base.endswith("/"):
        raise RuntimeError("PAGES_BASE_URL must be an https URL ending in /")
    # Upload the main video to YouTube and Facebook. These two receive the
    # landscape long-form master; Instagram receives only its vertical trailer.
    if not post.get("youtube_id"):
        post["youtube_id"] = upload_youtube(video, post, unlisted=youtube_unlisted)
        checkpoint(f"Record YouTube {kind} video", state)
    if not post.get("facebook_post_id"):
        post["facebook_post_id"] = publish_facebook(post, video, page_token, page_id)
        checkpoint(f"Record Facebook {kind} video", state)
    if not post.get("instagram_post_id"):
        relative = post.get("trailer_path") or post["video_path"]
        public_url = urljoin(base, relative)
        check_public(public_url, "video/")
        post["instagram_post_id"] = publish_instagram(post, public_url, ig_token, ig_id)
        checkpoint(f"Record Instagram {kind} Reel", state)
    if all((post.get("youtube_id"), post.get("facebook_post_id"), post.get("instagram_post_id"))):
        state.setdefault(f"{kind}_history", []).append({k: post[k] for k in post if k in {"quote_index", "episode", "youtube_id", "facebook_post_id", "instagram_post_id"}})
        if kind == "short":
            state["next_short_quote"] = post["quote_index"] + 1
        else:
            state["next_long_episode"] = post["episode"] + 1
        del state[key]
        checkpoint(f"Complete {kind} video publication", state)
        print(f"Published {kind} video to YouTube, Facebook and Instagram")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=("short", "long"))
    parser.add_argument("--youtube-unlisted", action="store_true")
    args = parser.parse_args()
    publish(args.kind, youtube_unlisted=args.youtube_unlisted)
