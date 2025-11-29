"""Fetch Depop listings and save them to data/products.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import time

import requests


DEFAULT_USERNAME = "shopy2z"
env_username = (os.getenv("DEPOP_USERNAME") or "").strip()
DEPOP_USERNAME = env_username or DEFAULT_USERNAME
API_URL = f"https://webapi.depop.com/api/v2/shop/{DEPOP_USERNAME}/products/"
DEFAULT_HEADERS = {
    "Accept": "application/json",
    # Depop returns 403s to generic clients; use a descriptive agent to reduce blocks.
    "User-Agent": os.getenv("DEPOP_USER_AGENT", "ZoesShopDataFetcher/1.0"),
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.depop.com/",
}
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"


def normalize_product(raw: dict[str, Any]) -> dict[str, str]:
    title = raw.get("title") or raw.get("name") or "Untitled item"

    price = raw.get("price") or {}
    amount = price.get("amount")
    price_text = price.get("price_string")
    if not price_text and amount is not None:
        price_text = f"${amount}"

    slug = raw.get("slug") or raw.get("id")
    url = raw.get("url") or (f"https://www.depop.com/products/{slug}/" if slug else "")

    images = raw.get("pictures") or raw.get("images") or []
    image_url = ""
    if images:
        first_image = images[0]
        if isinstance(first_image, dict):
            image_url = first_image.get("url") or first_image.get("large") or ""
        else:
            image_url = str(first_image)

    description = (raw.get("description") or "").strip()

    category_value: Any = raw.get("category") or raw.get("categories")
    category = "misc"
    if isinstance(category_value, list) and category_value:
        first_category = category_value[0]
        category = (
            first_category.get("name")
            or first_category.get("slug")
            if isinstance(first_category, dict)
            else str(first_category)
        ) or category
    elif isinstance(category_value, dict):
        category = category_value.get("name") or category_value.get("slug") or category

    tag = raw.get("brand") or category or "Depop find"

    return {
        "title": title,
        "price": price_text or "",
        "url": url,
        "image": image_url,
        "description": description,
        "category": category.lower(),
        "tag": tag,
    }


def fetch_products() -> Optional[list[dict[str, str]]]:
    attempts = 3
    backoff = 2.0
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                API_URL,
                params={"limit": 200},
                headers=DEFAULT_HEADERS,
                timeout=20,
            )
            response.raise_for_status()
            break
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else "?"
            print(
                f"Warning: Depop API returned HTTP {status} on attempt {attempt}/{attempts};"
                " retrying..." if attempt < attempts else " using cached products if available."
            )
            if status not in {429, 500, 502, 503, 504} or attempt == attempts:
                return None
        except requests.RequestException as exc:
            print(
                f"Warning: unable to reach Depop API on attempt {attempt}/{attempts} ({exc});"
                " retrying..." if attempt < attempts else " using cached products if available."
            )
            if attempt == attempts:
                return None

        time.sleep(backoff)
        backoff *= 2

    payload: Any = response.json()

    products = payload.get("products") or payload.get("items") or []
    normalized = [normalize_product(item) for item in products]

    # Filter out entries missing critical fields
    return [item for item in normalized if item["url"] and item["image"]]


def main() -> None:
    products = fetch_products()

    if not products:
        if OUTPUT_FILE.exists():
            cached = json.loads(OUTPUT_FILE.read_text())
            if cached:
                print(
                    "No fresh products fetched; keeping existing feed from"
                    f" {OUTPUT_FILE}."
                )
                return

        raise SystemExit(
            "No products fetched and no cached feed available; aborting without changes."
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(products, indent=2))
    print(f"Wrote {len(products)} products for {DEPOP_USERNAME} to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
