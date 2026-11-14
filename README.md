# Unlearn The Fear — no-paid-AI quote autoposter

This project generates 1080×1080 black-and-gold landscape quote JPGs using Python and a bank of 180 original quotes. No Canva or paid AI service is required. GitHub Actions can host the images using GitHub Pages and publish to the Unlearn The Fear Instagram Professional account and Facebook Page using Meta's Graph API.

**Scheduled publishing is ON as of 2026-11-14, following the owner's approval and a successful live test.** It is controlled by the versioned file `.github/auto-publish.txt` (the exact text `true` enables automatic posting; `false` pauses it). Manual workflow runs publish only when the Publish input is ON. Images and code are public, but access tokens must stay private in GitHub Actions Secrets.

## Step 1 — Enable Pages

Repository **Settings → Pages → Build and deployment → Source = GitHub Actions**. Do not use Deploy from branch: commits created by the workflow don't reliably trigger separate Pages builds.

## Step 2 — Add GitHub Actions variables

Repository **Settings → Secrets and variables → Actions → Variables**:

- `PAGES_BASE_URL` = `https://asucom-hash.github.io/unlearn-the-fear-autoposter/` (trailing slash is mandatory).
- `META_GRAPH_VERSION` = version supported by your Meta app; starter default is `v27.0`. Check the current available version.
- `META_IG_USER_ID` = numeric professional Instagram account ID linked to the Page.
- `META_PAGE_ID` = numeric Facebook Page ID.
- `ENABLE_AUTO_PUBLISH` was part of the initial setup. **It is now deprecated and ignored**; the live switch is `.github/auto-publish.txt`. The old variable can remain `false` without blocking the new schedule.

Under **Secrets**, add **two different secrets**: `META_IG_TOKEN` (Unified Login Instagram publishing token generated for @unlearnthefear) and `META_PAGE_TOKEN` (fresh Facebook Page publishing token), only after acquiring a properly scoped **Facebook Page access token** from your own Meta developer app. Never paste the token in a public GitHub file or in a chat.

## Step 3 — Preview without publishing

Open **Actions → Hourly Unlearn The Fear quotes → Run workflow**. Leave the Publish option OFF. The run tests the code, generates a JPEG, commits it to `docs/posts/`, and deploys it to GitHub Pages. Then visit:

https://asucom-hash.github.io/unlearn-the-fear-autoposter/posts/quote-0001.jpg

No post goes to Instagram or Facebook during this preview. Scheduled runs publish only when `.github/auto-publish.txt` contains `true`; otherwise they remain preview-only.

If the run fails at Pages deploy: check Pages source = GitHub Actions, actions are enabled, and the `github-pages` environment is allowed. To get a new preview from the first quote, retain the pending draft and rerun.

## Step 4 — Obtain your own Meta app access

Open https://developers.facebook.com/apps and create/configure an app for **Instagram API with Facebook Login**, linked to the Unlearn The Fear Facebook Page and Instagram professional account. Meta might require roles, App Review, permissions or business verification depending on how the app and accounts are configured.

Meta's Graph API Explorer: https://developers.facebook.com/tools/explorer/

Permissions normally needed: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`, and `pages_manage_posts`; extra permissions may apply for Business Manager setups.

With the correct user permissions, a common discovery call is:
`GET /me/accounts?fields=id,name,access_token,instagram_business_account`

Select the Unlearn the Fear Page. Set its numeric Page ID, the linked Instagram Professional account ID, and its Page access token as described above. For this Unified Login-based pipeline, **do not use the Page token for Instagram**. It uses `META_IG_TOKEN` for Instagram and `META_PAGE_TOKEN` for Facebook. Confirm that your Instagram token works with the `graph.facebook.com` Graph API route before enabling publishing. If your specific token is for `graph.instagram.com` instead, this starter needs a route-specific adjustment; do not enable publishing until the read-only token check passes.

**Security:** Access tokens expire or can be revoked. If you use a short-lived token from Graph API Explorer, the workflow will stop when it expires. Review Meta's long-lived token and renewal requirements before unattended publishing. Never enter tokens in GitHub Variables, plaintext repository files, logs, or screenshots.

## Step 5 — Check Meta tokens without posting

Go to **Actions → Hourly Unlearn The Fear quotes → Run workflow**. Leave Publish OFF and set **check_credentials ON**. This makes two read-only API requests using the separately stored tokens and reports whether the account IDs are accessible. Never paste either token in a GitHub variable, repository file or screenshot. If the test fails, leave publish OFF and check which Meta token type and permissions you received.

## Step 6 — Test one real post

After the preview JPEG is publicly accessible, and IDs and token are installed, go to Actions → Run workflow → **Publish ON**. This is a REAL post to both platforms. Verify each post and the IDs recorded in `state/state.json` before enabling scheduled publishing.

If one platform fails, inspect the GitHub Actions log. The state attempts to avoid repeating a successful post when retried, but external API failures can still produce rare duplicates.

## Step 7 — Enable the hourly schedule

The schedule is controlled by `.github/auto-publish.txt`, not by the deprecated repository variable. It currently contains `true` (LIVE). To pause, edit the file on the `main` branch and replace `true` with `false`; to resume change it back to `true`. Commit the change. The cron is at minute 23 of each UTC hour. GitHub may delay or skip scheduled runs; it is best effort, not guaranteed to run to the minute.

**Content limit:** 180 unique quote posts = 7.5 days at 24 posts per day. The pipeline stops when the bank runs out instead of silently repeating. Add original quotes to `quotes.json` to extend it.

**Costs:** These Python images need no paid AI API. GitHub Actions for public repos and GitHub Pages can be free within applicable usage rules, and Meta may impose rate/permission restrictions. Hourly posting can harm engagement; consider testing 1–3 posts a day first.

**Current status:** A live Meta API test on 2026-11-14 published quote 1 to both Instagram and Facebook, and the owner subsequently approved live scheduled publishing. GitHub Actions Secrets hold tokens; no token is stored in this repository. Rotate any previously exposed access tokens and review expiration/renewal. The GitHub connection does not transfer Windsor.ai tokens.
