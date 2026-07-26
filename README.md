# Streetwear Catalogue — self-updating

This repo rebuilds your streetwear catalogue automatically every day in the cloud
(GitHub Actions) and publishes it to a live web page (GitHub Pages). No computer needs
to be on. Your saved items are baked in and never lost.

## One-time setup (about 5 minutes)

1. Go to github.com → **New repository**. Name it e.g. `streetwear-catalogue`.
   Set it **Public** (Pages is free on public repos). Click **Create**.
2. On the new repo page click **uploading an existing file**, then drag in EVERYTHING
   from this folder (including the `.github` folder and the `rows` folder).
   Commit.  ⟶ *Easier route: install **GitHub Desktop**, drag this folder in, Publish.*
3. Repo → **Settings → Pages** → under "Build and deployment", Source = **GitHub Actions**.
4. Repo → **Settings → Actions → General** → Workflow permissions =
   **Read and write permissions** → Save.
5. Repo → **Actions** tab → click **Update catalogue** → **Run workflow** (first run now).
   After it finishes (a few minutes), your live catalogue is at:
   `https://<your-username>.github.io/streetwear-catalogue/`

That's it. From then on it rebuilds itself every day at 07:00 UK, folding in new stock
and flagging New Drops. Bookmark the URL.

## What updates automatically
- Fresh stock + prices for every brand in `brands.json`
- **New Drops** section = anything published in the last 7 days
- Starter outfits regenerate each run
- Your **saved items** (in `favourites.json` + snapshot in `rows/_saved.jsonl`) always show

## To add a brand
Edit `brands.json`, add `{"domain":"brand.com","brand":"Brand Name","cur":"USD"}`, commit.
It's in the next build.
