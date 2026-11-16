# Unlearn The Fear video automation

This is a separate video pipeline. It does not interrupt the existing quote-image workflow.

## What it makes

* **Daily video**: a 9:16, 1080×1920 narrated motivational Short for YouTube, Facebook and Instagram.
* **Tuesday and Friday reflection**: a 16:9 horizontal, 7+ minute guided reflection for YouTube and Facebook, plus a vertical Instagram Reel trailer that directs viewers to the full video.

All scripts are original to Unlearn The Fear. The renderer selects varied licence-checked Wikimedia Commons nature images, burns in captions, and creates an original low-volume ambient bed beneath the narration. It never uses an unlicensed music download.

## Required one-time secrets

Add these as repository **Actions Secrets**. Never place their values in files, variables, messages or screenshots.

| Secret | Purpose |
| --- | --- |
| `GOOGLE_TTS_API_KEY` | Restricted Google Cloud Text-to-Speech key. Restrict it to the Text-to-Speech API. |
| `YOUTUBE_TOKEN_JSON_B64` | Base64-encoded OAuth token JSON for the Unlearn The Fear channel, with only the `youtube.upload` scope. |
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

Create a Google Cloud project, enable YouTube Data API v3, and create a Desktop OAuth client. Complete its one-time Google consent using the Unlearn The Fear YouTube channel and the least-privileged `https://www.googleapis.com/auth/youtube.upload` scope. Store the returned `token.json` as base64 in `YOUTUBE_TOKEN_JSON_B64`. The refresh token renews access for future uploads without retaining your Google password.

## Costs and limits

Wikimedia Commons' public API needs no account or key. Google Cloud Text-to-Speech requires billing to be enabled even when its free allocation covers the use. A daily short plus two narrated reflections each week should be far below the free WaveNet allocation; set a Google billing budget alert as a safeguard. GitHub Actions minutes are consumed by video rendering, so check the repository owner's monthly Actions allowance.

## Image poster change after video launch

Keep the existing hourly image poster unchanged until the daily video is verified. After that, update `.github/workflows/hourly-quotes.yml` to four defined UTC slots per day, rather than its current hourly schedule.
