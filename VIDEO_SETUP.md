# Unlearn The Fear video automation

This is a separate video pipeline. It does not interrupt the existing quote-image workflow.

## What it makes

* **Daily video**: a 9:16, 1080×1920 narrated motivational Short for YouTube, Facebook and Instagram.
* **Tuesday and Friday reflection**: a 16:9 horizontal, 7+ minute guided reflection for YouTube and Facebook, plus a vertical Instagram Reel trailer that directs viewers to the full video.

All scripts are original to Unlearn The Fear. The renderer selects varied licence-checked Wikimedia Commons nature images, burns in captions, uses a local public-domain male neural voice, and creates an original low-volume ambient bed beneath the narration. It never uses an unlicensed music download.

## Required one-time secrets

Add these as repository **Actions Secrets**. Never place their values in files, variables, messages or screenshots.

| Secret | Purpose |
| --- | --- |
| `YOUTUBE_TOKEN_JSON_B64` | Encrypted GitHub-secret copy of the YouTube OAuth connection for the Unlearn The Fear channel. |
| `YOUTUBE_OAUTH_CLIENT_SECRET` | Google OAuth client secret, stored only in GitHub Actions Secrets. |
| `META_PAGE_TOKEN` | Already used by the Facebook image poster; also uploads native Facebook video. |
| `META_IG_TOKEN` | Already used by the Instagram image poster; also publishes Reels. |

The project already uses `META_PAGE_ID`, `META_IG_USER_ID`, `META_GRAPH_VERSION` and `PAGES_BASE_URL` Actions variables.

## Safe first test

1. Run **Daily Unlearn The Fear video** manually with **Publish ON** and **YouTube unlisted ON**.
2. It creates one real, unlisted YouTube Short and real Facebook/Instagram posts only when Publish is ON. For a private render-only check, leave Publish OFF.
3. Check the caption style, voice, clip choices, music level and platform posts.
4. Only after the test looks right, change `.github/video-auto-publish.txt` from `false` to `true`.
5. Run the long-form workflow manually the same way. Change `.github/longform-auto-publish.txt` to `true` only after it passes.

Scheduled daily video is 17:30 UTC. The twice-weekly long-form workflow runs Tuesday and Friday at 19:00 UTC. GitHub Actions schedules are UTC; adjust the cron values for British Summer Time if keeping an exact UK clock time matters.

## YouTube OAuth token

Create a Google Cloud project, enable YouTube Data API v3, configure the Google Auth platform, and create a **TVs and Limited Input devices** OAuth client. Store its client secret as `YOUTUBE_OAUTH_CLIENT_SECRET` in GitHub Actions Secrets. Run **Connect Unlearn The Fear YouTube uploader** in Actions, enter its public client ID, then approve the one-time Google device code using the Unlearn The Fear channel. The workflow encrypts the resulting refresh token directly into `YOUTUBE_TOKEN_JSON_B64`; it never stores your Google password or prints the token. Google's device flow requires the YouTube management scope, which includes uploads.

## Costs and limits

Wikimedia Commons' public API needs no account or key. The default Piper male voice model is public domain and runs in GitHub Actions; its approximately 60 MB model is cached after the first render. GitHub Actions minutes are consumed by video rendering, so check the repository owner's monthly Actions allowance.

## Image poster change after video launch

Keep the existing hourly image poster unchanged until the daily video is verified. After that, update `.github/workflows/hourly-quotes.yml` to four defined UTC slots per day, rather than its current hourly schedule.
