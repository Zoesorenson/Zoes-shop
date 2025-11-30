"""Fetch Depop listings and save them to data/products.json."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable, Optional

from urllib import error, parse, request


DEFAULT_USERNAME = "shopy2z"
env_username = (os.getenv("DEPOP_USERNAME") or "").strip()
DEPOP_USERNAME = env_username or DEFAULT_USERNAME
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    # Depop can return 403s to generic clients; mimic a real browser to reduce blocks.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": "https://www.depop.com",
}
DEPOP_COOKIE = (os.getenv("DEPOP_COOKIE") or "").strip()
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"


def _endpoint_urls(username: str) -> Iterable[tuple[str, str]]:
    yield "primary", f"https://webapi.depop.com/api/v2/shop/{username}/products/"
    # Fallback to the older endpoint if the v2 API blocks the request.
    yield "legacy", f"https://webapi.depop.com/api/v1/shop/{username}/products/"


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
    base_headers = {
        **DEFAULT_HEADERS,
        "Referer": f"https://www.depop.com/{DEPOP_USERNAME}/",
    }
    if DEPOP_COOKIE:
        base_headers["Cookie"] = DEPOP_COOKIE

    for label, url in _endpoint_urls(DEPOP_USERNAME):
        full_url = f"{url}?{parse.urlencode({'limit': 200})}"

        try:
            req = request.Request(full_url, headers=base_headers, method="GET")
            with request.urlopen(req, timeout=20) as resp:  # noqa: S310 - external URL fetch
                status = resp.status
                body = resp.read()
        except error.HTTPError as exc:
            status = exc.code
            print(
                f"Warning: Depop {label} endpoint returned HTTP {status}; "
                "trying next option."
            )
            if status in {400, 403}:
                print(
                    "Tip: Depop can block CI IPs or require a valid session. "
                    "Verify the username and try passing a DEPOP_COOKIE "
                    "environment variable with a logged-in cookie value."
                )
            continue
        except error.URLError as exc:
            print(
                f"Warning: unable to reach Depop {label} endpoint ({exc.reason}); "
                "trying next option."
            )
            continue

        try:
            payload: Any = json.loads(body)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            print(
                f"Warning: Depop {label} endpoint returned invalid JSON ({exc}); "
                "trying next option."
            )
            continue
        products = payload.get("products") or payload.get("items") or []
        normalized = [normalize_product(item) for item in products]
        filtered = [item for item in normalized if item["url"] and item["image"]]

        if filtered:
            return filtered

        print(
            f"Warning: Depop {label} endpoint returned no products; trying next option."
        )

    return None


def main() -> None:
    if not env_username:
        print("DEPOP_USERNAME not set; using default from script.")

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
