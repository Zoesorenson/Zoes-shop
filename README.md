# Zoe's Closet — GitHub Pages + Depop sync

This repo is a static storefront for a Depop shop. You can host it on GitHub Pages and keep the listings fresh by serving `data/products.json` and updating that file on a schedule.

## Deploying to GitHub Pages
1. Commit your changes and push to GitHub.
2. In your repository settings, enable **Pages** and select the `main` branch with the `/` root.
3. Your site will be published at `https://<username>.github.io/<repo>/` and will automatically serve `index.html`, `script.js`, and `data/products.json`.

## How the data loads
`script.js` fetches `data/products.json` on page load and every time a filter button is clicked. If the fetch fails (for example, while developing locally without the JSON), it falls back to the baked-in sample products.

## Automating the Depop feed with GitHub Actions
You can keep `data/products.json` in sync with your live Depop listings using the included scheduled workflow (`.github/workflows/refresh-depop-feed.yml`):

```yaml
name: Refresh Depop feed
on:
  schedule:
    - cron: "0 */6 * * *" # every 6 hours
  workflow_dispatch:

jobs:
  fetch-depop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Fetch Depop listings
        env:
          DEPOP_USERNAME: ${{ vars.DEPOP_USERNAME || vars.DEPOP_USER || vars.DEPOP_SHOP }}
        run: python scripts/fetch_depop.py
      - name: Commit updated feed
        run: |
          git config user.name "github-actions"
          git config user.email "actions@users.noreply.github.com"
          git add data/products.json
          git commit -m "chore: refresh depop feed" || echo "No changes"
          git push
```

### What the workflow does
- Runs every 6 hours (or on manual dispatch) to fetch products for `DEPOP_USERNAME` (default: `zoessorenson`).
- Writes the latest listings into `data/products.json` so the front end can render them.
- Commits and pushes the refreshed JSON so GitHub Pages serves the new data automatically.

### Configure your shop name
- Set a repository variable named `DEPOP_USERNAME` (or `DEPOP_USER` / `DEPOP_SHOP`) in **Settings → Secrets and variables → Actions**.
- The script uses the variable to call Depop's public API: `https://webapi.depop.com/api/v2/shop/<username>/products/`.

If the workflow cannot find any products, it fails without overwriting the existing `data/products.json`, keeping your storefront intact.
