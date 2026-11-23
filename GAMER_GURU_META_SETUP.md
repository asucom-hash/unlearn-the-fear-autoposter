# Gamer Guru native Meta Reels

This is a dedicated workflow for **Gamer Guru 312**. It does not modify the
Unlearn The Fear image or video workflows.

## What is already connected

The existing Meta app has permission to manage the Gamer Guru Facebook Page and
publish to `@gamerguru312` on Instagram. The Page and Instagram account were
read-only verified on 23 November 2026.

## One-time repository settings

Create these GitHub **Actions variables**:

| Name | Value |
| --- | --- |
| `GAMER_GURU_META_PAGE_ID` | Gamer Guru 312 Page's numeric ID |
| `GAMER_GURU_META_IG_USER_ID` | `@gamerguru312` professional account's numeric ID |
| `META_GRAPH_VERSION` | `v27.0` unless the Meta app is upgraded to a newer supported version |

Create these GitHub **Actions secrets** (never add them to a file, issue,
screenshot or chat):

| Name | Purpose |
| --- | --- |
| `GAMER_GURU_META_PAGE_TOKEN` | Page token with `pages_show_list`, `pages_read_engagement` and `pages_manage_posts` for Gamer Guru 312 |
| `GAMER_GURU_META_IG_TOKEN` | Instagram publishing token for `@gamerguru312`, with `instagram_basic` and `instagram_content_publish` |

Use the existing Meta app already selected in Graph API Explorer. It must remain
enabled for both the Gamer Guru Page and Instagram account. Store fresh,
properly-scoped credentials as GitHub Secrets; do not reuse the Unlearn The
Fear Page token, because Page tokens are Page-specific.

## Posting a Short

Open **Actions → Publish Gamer Guru Meta Reels → Run workflow**. For a safe
first run, leave **Publish** off; it makes read-only checks for both accounts.

For a real post, provide:

1. The original 9:16 MP4's **public direct HTTPS URL**. It must be reachable
   without sign-in by Meta's servers. A YouTube watch/Short link is not a media
   upload source and is intentionally rejected.
2. The title, caption and (optionally) the original YouTube Short URL.
3. **Publish = on**.

The workflow uses Meta's three-phase **Facebook Reels** upload API and native
Instagram Reels publishing. It records a successful Facebook upload before it
starts Instagram, so a retry does not duplicate the completed destination.

Facebook Reels must be public Page posts. The current API accepts vertical MP4
Reels from 3 to 90 seconds; 1080×1920 is recommended. Use the same master MP4
for Instagram rather than a thumbnail/link post.

## Important limitation

YouTube does not supply a supported direct source file URL for automatic Meta
Reel publishing. Upload or retain the original master MP4 before publishing the
YouTube Short. The workflow is ready to post it to Facebook and Instagram once
that original file has a public direct HTTPS URL.

X is not a Meta platform; continue to publish the same native video plus the
YouTube link through the connected X account.
