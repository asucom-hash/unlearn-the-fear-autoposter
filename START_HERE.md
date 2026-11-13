# START HERE — Unlearn The Fear

Your connected GitHub repo is [asucom-hash/unlearn-the-fear-autoposter](https://github.com/asucom-hash/unlearn-the-fear-autoposter).

1. Open the repository → **Settings → Pages**, choose **GitHub Actions** as the source.
2. Open **Settings → Secrets and variables → Actions → Variables**. Add `PAGES_BASE_URL=https://asucom-hash.github.io/unlearn-the-fear-autoposter/` and `ENABLE_AUTO_PUBLISH=false`.
3. Open **Actions → Hourly Unlearn The Fear quotes → Run workflow**, keep the **Publish** checkbox OFF.
4. Confirm the hosted first image at https://asucom-hash.github.io/unlearn-the-fear-autoposter/posts/quote-0001.jpg
5. Create/configure Meta Developer app and add the account IDs as GitHub Variables and a Page token as GitHub Secret. See README.
6. Test one real live publication manually with Publish ON, verify both posts, then change `ENABLE_AUTO_PUBLISH=true` if desired.

**No public social posts are made until you explicitly enable publishing.** Never enter Meta access tokens into a public repository or this chat.
