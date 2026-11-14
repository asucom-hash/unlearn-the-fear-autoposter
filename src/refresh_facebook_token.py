"""Renew the Facebook Page token without printing any credentials.

The workflow keeps a long-lived User token in META_USER_TOKEN.  It refreshes
that token when it is near expiry, derives a Page token, and stores both values
back in GitHub Actions Secrets using a repository-scoped fine-grained token.
"""
from __future__ import annotations

import base64
import os
import time

import requests
from nacl import encoding, public

VERSION = os.getenv("META_GRAPH_VERSION", "v27.0").strip()
GRAPH = "https://graph.facebook.com/" + VERSION + "/"
REFRESH_WINDOW_SECONDS = 21 * 24 * 60 * 60


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            "Missing " + name
            + ". Configure the Facebook token-renewal secrets before publishing."
        )
    return value


def graph_get(path: str, params: dict[str, str]) -> dict:
    try:
        response = requests.get(GRAPH + path, params=params, timeout=30)
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("Meta token renewal request failed") from exc
    if not response.ok or "error" in body:
        error = body.get("error") or {}
        raise RuntimeError(
            "Meta token renewal rejected (code "
            + str(error.get("code", response.status_code))
            + ")."
        )
    return body


def user_token_expiry(user_token: str, app_id: str, app_secret: str) -> int:
    body = graph_get(
        "debug_token",
        {
            "input_token": user_token,
            "access_token": app_id + "|" + app_secret,
        },
    )
    data = body.get("data") or {}
    if not data.get("is_valid"):
        raise RuntimeError(
            "META_USER_TOKEN is invalid. Generate a fresh bootstrap User token, "
            "then run the read-only credential check again."
        )
    return int(data.get("expires_at") or 0)


def refresh_user_token(user_token: str, app_id: str, app_secret: str) -> str:
    body = graph_get(
        "oauth/access_token",
        {
            "grant_type": "fb_exchange_token",
            "client_id": app_id,
            "client_secret": app_secret,
            "fb_exchange_token": user_token,
        },
    )
    token = str(body.get("access_token") or "").strip()
    if not token:
        raise RuntimeError("Meta did not return a refreshed User token.")
    return token


def page_token_for(user_token: str, page_id: str) -> str:
    body = graph_get(
        "me/accounts",
        {
            "fields": "id,name,access_token,tasks",
            "access_token": user_token,
        },
    )
    for account in body.get("data") or []:
        if str(account.get("id")) == page_id:
            token = str(account.get("access_token") or "").strip()
            if token:
                return token
    raise RuntimeError(
        "The configured Facebook Page is not available to META_USER_TOKEN. "
        "Re-authorize the app with that Page selected."
    )


def page_token_is_valid(page_token: str, page_id: str) -> bool:
    if not page_token:
        return False
    try:
        body = graph_get(
            page_id,
            {
                "fields": "id,name",
                "access_token": page_token,
            },
        )
    except RuntimeError:
        return False
    return str(body.get("id")) == page_id


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2026-03-10",
    }


def update_github_secret(name: str, value: str, repository: str, token: str) -> None:
    base = "https://api.github.com/repos/" + repository + "/actions/secrets"
    try:
        key_response = requests.get(base + "/public-key", headers=github_headers(token), timeout=30)
        key_body = key_response.json()
        if not key_response.ok:
            raise RuntimeError()
        key = public.PublicKey(
            key_body["key"].encode("utf-8"), encoding.Base64Encoder
        )
        encrypted = base64.b64encode(public.SealedBox(key).encrypt(value.encode("utf-8"))).decode("ascii")
        put_response = requests.put(
            base + "/" + name,
            headers=github_headers(token),
            json={"encrypted_value": encrypted, "key_id": key_body["key_id"]},
            timeout=30,
        )
    except (KeyError, requests.RequestException, ValueError) as exc:
        raise RuntimeError("Could not securely update GitHub Actions secrets.") from exc
    if put_response.status_code not in (201, 204):
        raise RuntimeError(
            "GitHub could not update " + name
            + ". Check META_GITHUB_SECRETS_TOKEN has repository Secrets write access."
        )


def expose_to_this_job(name: str, value: str) -> None:
    # GitHub masks the value before any later step can write it to logs.
    print("::add-mask::" + value)
    env_file = os.getenv("GITHUB_ENV", "")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as handle:
            handle.write(name + "<<EOF\n" + value + "\nEOF\n")


def main() -> None:
    user_token = require("META_USER_TOKEN")
    app_id = require("META_APP_ID")
    app_secret = require("META_APP_SECRET")
    repository = require("GITHUB_REPOSITORY")
    secrets_token = require("META_GITHUB_SECRETS_TOKEN")
    page_id = require("META_PAGE_ID")
    current_page_token = os.getenv("META_PAGE_TOKEN", "").strip()

    expiry = user_token_expiry(user_token, app_id, app_secret)
    force = os.getenv("META_FORCE_TOKEN_REFRESH", "").lower() == "true"
    refresh_due = force or not expiry or expiry - int(time.time()) < REFRESH_WINDOW_SECONDS
    usable_page_token = page_token_is_valid(current_page_token, page_id)

    refreshed_user_token = user_token
    if refresh_due:
        refreshed_user_token = refresh_user_token(user_token, app_id, app_secret)

    new_page_token = current_page_token
    if refresh_due or not usable_page_token:
        new_page_token = page_token_for(refreshed_user_token, page_id)
        if not page_token_is_valid(new_page_token, page_id):
            raise RuntimeError("Meta returned a Facebook Page token that failed validation.")

    changed_user = refreshed_user_token != user_token
    changed_page = new_page_token != current_page_token
    if changed_user:
        update_github_secret(
            "META_USER_TOKEN", refreshed_user_token, repository, secrets_token
        )
        expose_to_this_job("META_USER_TOKEN", refreshed_user_token)
    if changed_page:
        update_github_secret(
            "META_PAGE_TOKEN", new_page_token, repository, secrets_token
        )
        expose_to_this_job("META_PAGE_TOKEN", new_page_token)

    if changed_user or changed_page:
        print("Facebook credentials renewed and stored securely.")
    else:
        print("Facebook credentials are healthy; renewal is not due.")


if __name__ == "__main__":
    main()
