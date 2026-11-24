"""Renew Gamer Guru Meta credentials using the existing secured Meta refresh configuration."""
from __future__ import annotations

import os
import time

from refresh_facebook_token import (
    expose_to_this_job,
    graph_get,
    page_token_for,
    require,
    refresh_user_token,
    update_github_secret,
    user_token_expiry,
)

REFRESH_WINDOW_SECONDS = 21 * 24 * 60 * 60


def ig_token_is_valid(token: str, ig_id: str) -> bool:
    try:
        account = graph_get(ig_id, {"fields": "id,username", "access_token": token})
    except RuntimeError:
        return False
    return str(account.get("id")) == ig_id and str(account.get("username", "")).lower() == "gamerguru312"


def main() -> None:
    user_token = require("META_USER_TOKEN")
    app_id = require("META_APP_ID")
    app_secret = require("META_APP_SECRET")
    github_token = require("META_GITHUB_SECRETS_TOKEN")
    repository = require("GITHUB_REPOSITORY")
    page_id = require("GAMER_GURU_META_PAGE_ID")
    ig_id = require("GAMER_GURU_META_IG_USER_ID")
    old_page_token = os.getenv("GAMER_GURU_META_PAGE_TOKEN", "").strip()
    old_ig_token = os.getenv("GAMER_GURU_META_IG_TOKEN", "").strip()

    expiry = user_token_expiry(user_token, app_id, app_secret)
    refresh_due = not expiry or expiry - int(time.time()) < REFRESH_WINDOW_SECONDS
    refreshed_user_token = refresh_user_token(user_token, app_id, app_secret) if refresh_due else user_token

    new_page_token = page_token_for(refreshed_user_token, page_id)
    if not ig_token_is_valid(refreshed_user_token, ig_id):
        raise RuntimeError(
            "The existing Meta User token cannot access @gamerguru312. "
            "Re-authorize the existing Meta app with Instagram publishing access."
        )

    if refreshed_user_token != user_token:
        update_github_secret("META_USER_TOKEN", refreshed_user_token, repository, github_token)
        expose_to_this_job("META_USER_TOKEN", refreshed_user_token)
    if new_page_token != old_page_token:
        update_github_secret("GAMER_GURU_META_PAGE_TOKEN", new_page_token, repository, github_token)
        expose_to_this_job("GAMER_GURU_META_PAGE_TOKEN", new_page_token)
    if refreshed_user_token != old_ig_token:
        update_github_secret("GAMER_GURU_META_IG_TOKEN", refreshed_user_token, repository, github_token)
        expose_to_this_job("GAMER_GURU_META_IG_TOKEN", refreshed_user_token)

    print("Gamer Guru Meta credentials renewed and stored securely.")


if __name__ == "__main__":
    main()
