"""Publish an image safely to Instagram and Facebook with idempotent checkpoints."""
import os
import subprocess
import time

import requests

from prepare import ROOT, load_state, save_state


class MetaRateLimitError(RuntimeError):
    pass


class MetaMediaProcessingError(RuntimeError):
    pass


def graph(method, path, params):
    version = os.getenv("META_GRAPH_VERSION", "v27.0").strip()
    response = requests.request(
        method,
        "https://graph.facebook.com/" + version + "/" + path,
        params=params if method == "GET" else None,
        data=params if method == "POST" else None,
        timeout=35,
    )
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError("Meta returned non-JSON HTTP " + str(response.status_code)) from exc
    if not response.ok or "error" in body:
        error = body.get("error", {})
        message = "Meta error: code=" + str(error.get("code")) + " " + str(error.get("message", ""))[:300]
        if error.get("code") == 4:
            usage = response.headers.get("x-app-usage", "not supplied")
            raise MetaRateLimitError(message + "; X-App-Usage=" + usage)
        raise RuntimeError(message)
    return body


def checkpoint(message, state):
    save_state(state)
    subprocess.run(["git", "add", "state/state.json"], cwd=ROOT, check=True)
    changed = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if changed.returncode:
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=github-actions[bot]",
                "-c",
                "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                "commit",
                "-m",
                message,
            ],
            cwd=ROOT,
            check=True,
        )
        subprocess.run(["git", "push"], cwd=ROOT, check=True)


def image_url(image_path):
    """Prefer an immutable raw GitHub URL so Meta never races a Pages deployment."""
    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()
    path = str(image_path).lstrip("/")
    if repository and revision:
        return f"https://raw.githubusercontent.com/{repository}/{revision}/docs/{path}"

    base = os.getenv("PAGES_BASE_URL", "").strip()
    if not base.startswith("https://") or not base.endswith("/"):
        raise RuntimeError("Missing a usable GitHub repository URL or PAGES_BASE_URL")
    return base + path


def main():
    state = load_state()
    post = state.get("pending")
    if not post:
        print("Nothing pending.")
        return

    image = image_url(post["image_path"])
    page = os.getenv("META_PAGE_ID", "").strip()
    instagram = os.getenv("META_IG_USER_ID", "").strip()
    instagram_token = os.getenv("META_IG_TOKEN", "").strip()
    page_token = os.getenv("META_PAGE_TOKEN", "").strip()
    if not (page and instagram and instagram_token and page_token):
        raise RuntimeError("Missing account IDs or META_IG_TOKEN / META_PAGE_TOKEN secrets")

    # Each response-producing API call below is itself a credential check. Removing
    # pre-flight API reads keeps the publisher under Meta's app request allowance.
    try:
        if not post.get("instagram_post_id"):
            creation_id = post.get("instagram_creation_id")
            if not creation_id:
                container = graph(
                    "POST",
                    instagram + "/media",
                    {"image_url": image, "caption": post["caption"], "access_token": instagram_token},
                )
                creation_id = container["id"]
                post["instagram_creation_id"] = creation_id
                checkpoint("Record Instagram media container", state)

            # Allow processing to begin before the first poll and cap polling at five
            # requests. The next scheduled run resumes the same container if needed.
            time.sleep(12)
            ready = False
            for attempt in range(5):
                status = graph(
                    "GET",
                    creation_id,
                    {"fields": "status_code", "access_token": instagram_token},
                ).get("status_code")
                if status == "FINISHED":
                    ready = True
                    break
                if status in ("ERROR", "EXPIRED"):
                    raise MetaMediaProcessingError(
                        "Instagram processing failed: " + status + "; source=" + image
                    )
                if attempt < 4:
                    time.sleep(12)
            if not ready:
                print("Instagram image is still processing; deferred without creating a duplicate.")
                return

            published = graph(
                "POST",
                instagram + "/media_publish",
                {"creation_id": creation_id, "access_token": instagram_token},
            )
            post["instagram_post_id"] = published["id"]
            post.pop("instagram_creation_id", None)
            checkpoint("Record Instagram post", state)

        if not post.get("facebook_post_id"):
            published = graph(
                "POST",
                page + "/photos",
                {
                    "url": image,
                    "caption": post["caption"],
                    "published": "true",
                    "access_token": page_token,
                },
            )
            post["facebook_post_id"] = published.get("post_id") or published["id"]
            checkpoint("Record Facebook post", state)
    except MetaRateLimitError as exc:
        print("Meta rate limit; publication deferred without creating a duplicate: " + str(exc))
        return
    except MetaMediaProcessingError as exc:
        # A terminal container can never be published. Discard only it; retain the
        # pending image and all completed-platform IDs for an idempotent retry.
        post.pop("instagram_creation_id", None)
        checkpoint("Discard failed Instagram media container", state)
        print("Instagram processing failed; publication deferred for a fresh container: " + str(exc))
        return

    if post.get("instagram_post_id") and post.get("facebook_post_id"):
        state.setdefault("history", []).append(
            {
                "quote_index": post["quote_index"],
                "instagram_post_id": post["instagram_post_id"],
                "facebook_post_id": post["facebook_post_id"],
            }
        )
        state["next_quote"] = post["quote_index"] + 1
        del state["pending"]
        checkpoint("Complete quote publication", state)
        print("Both platforms published successfully")


if __name__ == "__main__":
    main()
