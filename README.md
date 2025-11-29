# Zoe's Closet — GitHub Pages + Depop sync

This repo is a static storefront for a Depop shop. You can host it on GitHub Pages and keep the listings fresh by serving `data/products.json` and updating that file on a schedule.

## Deploying to GitHub Pages
1. Commit your changes and push to GitHub.
2. In your repository settings, enable **Pages** and select the `main` branch with the `/` root.
3. Your site will be published at `https://<username>.github.io/<repo>/` and will automatically serve `index.html`, `script.js`, and `data/products.json`.

## How the data loads
`script.js` fetches `data/products.json` on page load and every time a filter button is clicked. If the fetch fails (for example, while developing locally without the JSON), it falls back to the baked-in sample products.

## Automating the Depop feed with GitHub Actions
You can keep `data/products.json` in sync with your live Depop listings using a scheduled workflow:

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
      - name: Scrape Depop listings
        run: |
          python - <<'PY'
          import json, requests
          from bs4 import BeautifulSoup

          url = "https://www.depop.com/zoessorenson/"
          html = requests.get(url, timeout=10).text
          soup = BeautifulSoup(html, "html.parser")
          # Replace this with real parsing of your listing cards
          listings = []
          with open("data/products.json", "w") as f:
            json.dump(listings, f, indent=2)
          PY
      - name: Commit updated feed
        run: |
          git config user.name "github-actions"
          git config user.email "actions@users.noreply.github.com"
          git add data/products.json
          git commit -m "chore: refresh depop feed" || echo "No changes"
          git push
```

The workflow fetches your Depop page, parses listings into `data/products.json`, and pushes the refreshed JSON back to the repo. GitHub Pages will publish the new data automatically, so visitors always see the latest items.
