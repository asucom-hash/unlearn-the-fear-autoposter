"""Complete a one-time YouTube device-flow connection without logging tokens.

This runs only from the manual ``Connect YouTube uploader`` GitHub workflow.
The user authorises the displayed one-time code in Google's own page; the
resulting refresh token is encrypted directly into this repository's Actions
Secrets using the existing, repository-scoped secrets-write token.
"""
from __future__ import annotations

import base64
import json
import os
import time
from datetime import UTC, datetime, timedelta

import requests
from nacl import encoding, public


DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
# Google's device flow supports the broad YouTube management scope, rather
# than the narrower upload-only scope. It is still limited to YouTube.
YOUTUBE_SCOPE = "https://www.googleapis.com/auth/youtube"


def require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}.")
    return value


def github_headers(token: str) -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer " + token,
        "X-GitHub-Api-Version": "2026-03-10",
    }


def store_github_secret(name: str, value: str, repository: str, github_token: str) -> None:
    """Encrypt a secret client-side before sending it to GitHub's Secrets API."""
    base = f"https://api.github.com/repos/{repository}/actions/secrets"
    key_response = requests.get(base + "/public-key", headers=github_headers(github_token), timeout=30)
    if not key_response.ok:
        raise RuntimeError("GitHub could not retrieve the repository secret key.")
    key_body = key_response.json()
    try:
        key = public.PublicKey(key_body["key"].encode("utf-8"), encoding.Base64Encoder)
        encrypted = base64.b64encode(public.SealedBox(key).encrypt(value.encode("utf-8"))).decode("ascii")
        key_id = key_body["key_id"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("GitHub returned an invalid repository secret key.") from exc
    saved = requests.put(
        f"{base}/{name}",
        headers=github_headers(github_token),
        json={"encrypted_value": encrypted, "key_id": key_id},
        timeout=30,
    )
    if saved.status_code not in (201, 204):
        raise RuntimeError("GitHub could not securely save the YouTube connection.")


def request_device_code(client_id: str) -> dict:
    response = requests.post(
        DEVICE_CODE_URL,
        data={"client_id": client_id, "scope": YOUTUBE_SCOPE},
        timeout=30,
    )
    if not response.ok:
        raise RuntimeError("Google did not issue a device authorisation code.")
    body = response.json()
    if not all(body.get(key) for key in ("device_code", "user_code", "verification_url")):
        raise RuntimeError("Google returned an incomplete device authorisation response.")
    return body


def wait_for_tokens(client_id: str, device: dict) -> dict:
    deadline = time.monotonic() + int(device.get("expires_in", 1800))
    interval = max(5, int(device.get("interval", 5)))
    while time.monotonic() < deadline:
        time.sleep(interval)
        response = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "device_code": device["device_code"],
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
            timeout=30,
        )
        body = response.json()
        if response.ok and body.get("access_token") and body.get("refresh_token"):
            return body
        error = body.get("error")
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "access_denied":
            raise RuntimeError("Google authorisation was declined.")
        if error == "expired_token":
            raise RuntimeError("The Google authorisation code expired. Start a new connection run.")
        detail = str(body.get("error_description") or "").strip()
        suffix = f" ({error}: {detail})" if detail else f" ({error or 'unknown error'})"
        raise RuntimeError("Google could not complete the YouTube authorisation" + suffix)
    raise RuntimeError("The Google authorisation code expired. Start a new connection run.")


def main() -> None:
    client_id = require("YOUTUBE_OAUTH_CLIENT_ID")
    github_token = require("META_GITHUB_SECRETS_TOKEN")
    repository = require("GITHUB_REPOSITORY")

    device = request_device_code(client_id)
    print("Open " + device["verification_url"] + " in the Google account that owns Unlearn The Fear.")
    print("Enter this one-time code: " + device["user_code"])
    print("This run will wait for your approval, then save the connection privately.")

    tokens = wait_for_tokens(client_id, device)
    expiry = datetime.now(UTC) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    token_document = {
        "token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_uri": TOKEN_URL,
        "client_id": client_id,
        # A TV/limited-input OAuth client is a public client. The key is kept
        # for compatibility with google-auth's authorised-user JSON format.
        "client_secret": None,
        "scopes": [YOUTUBE_SCOPE],
        "expiry": expiry.isoformat(),
    }
    encoded = base64.b64encode(json.dumps(token_document, separators=(",", ":")).encode("utf-8")).decode("ascii")
    print("::add-mask::" + tokens["access_token"])
    print("::add-mask::" + tokens["refresh_token"])
    print("::add-mask::" + encoded)
    store_github_secret("YOUTUBE_TOKEN_JSON_B64", encoded, repository, github_token)
    print("YouTube upload connection stored securely in Actions Secrets.")


if __name__ == "__main__":
    main()
