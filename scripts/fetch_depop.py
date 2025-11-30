"""Fetch Depop listings and save them to data/products.json."""
from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable, NamedTuple, Optional, Sequence

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
CANONICAL_CATEGORIES = ("tops", "bottoms", "outerwear", "accessories")
CATEGORY_KEYWORDS = {
    "outerwear": (
        "coat",
        "jacket",
        "outerwear",
        "puffer",
        "windbreaker",
        "shell",
        "parka",
        "blazer",
        "trench",
        "fleece",
        "gilet",
    ),
    "tops": (
        "top",
        "tee",
        "t-shirt",
        "shirt",
        "sweater",
        "jumper",
        "hoodie",
        "crewneck",
        "cardigan",
        "sweatshirt",
        "pullover",
        "vest",
        "crew",
        "bodysuit",
        "body suit",
        "blouse",
        "polo",
        "tank",
        "camisole",
        "long sleeve",
        "quarter zip",
        "dress",
    ),
    "bottoms": (
        "bottom",
        "jean",
        "denim",
        "pant",
        "trouser",
        "short",
        "trunk",
        "swim",
        "skirt",
        "legging",
        "cargo",
        "sweatpant",
        "jogger",
    ),
    "accessories": (
        "accessories",
        "accessory",
        "bag",
        "purse",
        "tote",
        "wallet",
        "necklace",
        "bracelet",
        "ring",
        "earring",
        "jewelry",
        "belt",
        "scarf",
        "beanie",
        "hat",
        "cap",
        "sunglasses",
        "glove",
        "sandal",
        "shoe",
        "sneaker",
        "boot",
        "loafer",
        "heel",
    ),
}
OUTPUT_FILE = Path(__file__).resolve().parent.parent / "data" / "products.json"
COOKIE_FILE = Path(__file__).resolve().parent.parent / "depop.cookie"


def _load_cookie() -> tuple[str, Optional[str]]:
    env_cookie = (os.getenv("DEPOP_COOKIE") or "").strip()
    if env_cookie:
        return env_cookie, "DEPOP_COOKIE environment variable"

    cookie_path = os.getenv("DEPOP_COOKIE_FILE")
    if cookie_path:
        path = Path(cookie_path)
        if path.exists():
            return path.read_text().strip(), str(path)

    if COOKIE_FILE.exists():
        return COOKIE_FILE.read_text().strip(), str(COOKIE_FILE)

    return "", None


DEPOP_COOKIE, DEPOP_COOKIE_SOURCE = _load_cookie()
DISABLE_PROXY = os.getenv("DEPOP_DISABLE_PROXY") == "1"


class FetchResult(NamedTuple):
    products: Optional[list[dict[str, str]]]
    blocked: bool


def _endpoint_urls(username: str) -> Iterable[tuple[str, str]]:
    yield "primary", f"https://webapi.depop.com/api/v2/shop/{username}/products/"
    # Fallback to the older endpoint if the v2 API blocks the request.
    yield "legacy", f"https://webapi.depop.com/api/v1/shop/{username}/products/"


def _canonicalize_category(*candidates: str) -> str:
    """Map Depop category text to one of the UI buckets."""
    def _matches(value: str, keyword: str) -> bool:
        return bool(re.search(rf"\b{re.escape(keyword)}\w*", value))

    normalized = []
    for value in candidates:
        cleaned = (value or "").strip().lower()
        if cleaned:
            normalized.append(cleaned)

    for value in normalized:
        if value in CANONICAL_CATEGORIES:
            return value

    for value in normalized:
        for canonical, keywords in CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if _matches(value, keyword):
                    return canonical

    combined = " ".join(normalized)
    for canonical, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if _matches(combined, keyword):
                return canonical

    return "misc"


def _is_sold(raw: dict[str, Any]) -> bool:
    """Return True when Depop marks an item as sold or unavailable."""
    status_fields = (
        str(raw.get("status") or raw.get("state") or "").lower(),
        str(raw.get("visibility") or "").lower(),
    )

    sold_markers = {"sold", "sold_out", "sold-out", "sold out", "unavailable"}
    if any(status in sold_markers for status in status_fields):
        return True

    if raw.get("sold") is True:
        return True

    # Depop sometimes exposes availability as a boolean or int.
    available = raw.get("available")
    if available in (False, 0):
        return True

    return False


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

    canonical_category = _canonicalize_category(category, title, description, tag)

    return {
        "title": title,
        "price": price_text or "",
        "url": url,
        "image": image_url,
        "description": description,
        "category": canonical_category,
        "tag": tag,
    }


def fetch_products() -> FetchResult:
    blocked = False
    base_headers = {
        **DEFAULT_HEADERS,
        "Referer": f"https://www.depop.com/{DEPOP_USERNAME}/",
    }
    if DEPOP_COOKIE:
        base_headers["Cookie"] = DEPOP_COOKIE

    if DEPOP_COOKIE_SOURCE:
        print(f"Using Depop cookie from {DEPOP_COOKIE_SOURCE}")

    handlers = []
    if DISABLE_PROXY:
        handlers.append(request.ProxyHandler({}))
    opener = request.build_opener(*handlers)

    for label, url in _endpoint_urls(DEPOP_USERNAME):
        full_url = f"{url}?{parse.urlencode({'limit': 200})}"

        try:
            req = request.Request(full_url, headers=base_headers, method="GET")
            with opener.open(req, timeout=20) as resp:  # noqa: S310 - external URL fetch
                status = resp.status
                body = resp.read()
        except error.HTTPError as exc:
            status = exc.code
            if status in {400, 403}:
                blocked = True
            print(
                f"Warning: Depop {label} endpoint returned HTTP {status}; "
                "trying next option."
            )
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
            reason_text = str(getattr(exc, "reason", exc))
            if "403" in reason_text and not DISABLE_PROXY:
                blocked = True
                print(
                    "Tip: if a corporate proxy is blocking Depop, set DEPOP_DISABLE_PROXY=1 "
                    "to ignore system proxy settings."
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
        filtered_products = [item for item in products if not _is_sold(item)]
        if filtered_products:
            kept_products = filtered_products
            if len(filtered_products) != len(products):
                print(
                    f"Filtered out {len(products) - len(filtered_products)} sold items "
                    f"from Depop {label} response."
                )
        elif products:
            print(
                "Warning: Depop response flagged everything as sold; "
                "keeping unfiltered products to avoid an empty feed."
            )
            kept_products = products
        else:
            kept_products = products

        normalized = [normalize_product(item) for item in kept_products]
        filtered = [item for item in normalized if item["url"] and item["image"]]

        if filtered:
            return FetchResult(filtered, blocked)

        print(
            f"Warning: Depop {label} endpoint returned no products; trying next option."
        )

    return FetchResult(None, blocked)


def _strip_suffix(text: str, suffix: str) -> str:
    if text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def _extract_hashtag(text: str) -> str:
    match = re.search(r"#(\\w+)", text)
    return match.group(1) if match else ""


def _cache_depop_cookies(cookies: Sequence[dict[str, Any]], action: str) -> bool:
    depop_cookies = [
        cookie for cookie in cookies if "depop" in (cookie.get("domain") or "")
    ]
    cookie_header = "; ".join(
        f"{cookie['name']}={cookie['value']}"
        for cookie in depop_cookies
        if cookie.get("name") and cookie.get("value")
    )
    if cookie_header:
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(cookie_header)
        print(f"{action} {COOKIE_FILE}")
        return True

    print("Warning: no Depop cookies found to cache.")
    return False


async def _refresh_cookie_with_playwright(username: str) -> bool:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - optional dependency
        print(
            "Playwright is not installed; skipping cookie refresh. "
            "Install it with 'pip install playwright' and "
            "'python -m playwright install chromium'."
        )
        return False

    headless_env = (os.getenv("DEPOP_PLAYWRIGHT_HEADLESS") or "").lower()
    headless = headless_env in {"1", "true", "yes"}
    if headless:
        print("Warning: headless Playwright is likely to be blocked; forcing visible browser.")
        headless = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        shop_url = f"https://www.depop.com/{username}/"
        await page.goto(shop_url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3_000)
        await page.close()

        try:
            cookies = await context.cookies()
            return _cache_depop_cookies(cookies, "Refreshed Depop cookies in")
        finally:
            await browser.close()


async def _scrape_with_playwright(username: str) -> list[dict[str, str]]:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "Playwright is not installed. Run 'pip install playwright' "
            "and 'python -m playwright install chromium'."
        ) from exc

    products: list[dict[str, str]] = []

    async with async_playwright() as p:
        # Headless requests are blocked by Depop/Cloudflare; use a visible browser.
        headless_env = (os.getenv("DEPOP_PLAYWRIGHT_HEADLESS") or "").lower()
        headless = headless_env in {"1", "true", "yes"}
        if headless:
            print("Warning: headless Playwright is likely to be blocked; forcing visible browser.")
            headless = False

        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()

        shop_url = f"https://www.depop.com/{username}/"
        page = await context.new_page()
        await page.goto(shop_url, wait_until="domcontentloaded", timeout=60_000)
        await page.wait_for_timeout(3_000)

        # Grab product links from the grid.
        link_js = """
        () => Array.from(
            document.querySelectorAll(".styles_productCardRoot__DaYPT a[href*='/products/']")
        ).map((el) => el.href)
        """
        links: Sequence[str] = await page.evaluate(link_js)
        await page.close()

        seen = set()
        for link in links:
            if not link or link in seen:
                continue
            seen.add(link)

            item_page = await context.new_page()
            try:
                await item_page.goto(link, wait_until="domcontentloaded", timeout=60_000)
                await item_page.wait_for_timeout(2_000)

                buy_now_cta = await item_page.locator("button:has-text('Buy now')").count()
                add_to_bag_cta = await item_page.locator(
                    "button:has-text('Add to bag')"
                ).count()
                sold_cta = await item_page.locator("button:has-text('Sold')").count()
                if sold_cta or (buy_now_cta + add_to_bag_cta) == 0:
                    print(f"Skipping sold Depop listing: {link}")
                    continue

                async def _get_meta(prop: str) -> str:
                    selector = f"meta[property='{prop}']"
                    value = await item_page.eval_on_selector(
                        selector, "el => el ? el.content : ''"
                    )
                    return value or ""

                og_title = await _get_meta("og:title")
                og_desc = await _get_meta("og:description")
                og_image = await _get_meta("og:image")

                body_text = await item_page.locator("body").inner_text()
                price_match = re.search(r"\\$\\d[\\d.,]*", body_text)

                title = _strip_suffix(og_title, " | Depop").strip() or "Depop item"
                description = (og_desc or "").strip()
                price = price_match.group(0) if price_match else ""

                tag = _extract_hashtag(description) or "Depop find"
                category = _canonicalize_category(tag, title, description)

                products.append(
                    {
                        "title": title,
                        "price": price,
                        "url": link,
                        "image": og_image,
                        "description": description,
                        "category": category,
                        "tag": tag,
                    }
                )
            finally:
                await item_page.close()

        try:
            cookies = await context.cookies()
            _cache_depop_cookies(cookies, "Cached Depop cookies to")
        except Exception as exc:  # pragma: no cover - defensive
            print(f"Warning: unable to cache Depop cookies from Playwright: {exc}")
        finally:
            await browser.close()

    return products


def main() -> None:
    if not env_username:
        print("DEPOP_USERNAME not set; using default from script.")

    result = fetch_products()
    products = result.products
    blocked = result.blocked

    if blocked:
        print("Depop API blocked the request; refreshing cookie with Playwright...")
        try:
            refreshed = asyncio.run(_refresh_cookie_with_playwright(DEPOP_USERNAME))
        except Exception as exc:  # pragma: no cover - runtime only
            print(f"Cookie refresh failed: {exc}")
            refreshed = False

        if refreshed:
            retry_result = fetch_products()
            products = retry_result.products or products
            blocked = retry_result.blocked

    if not products:
        print("HTTP scrape failed; trying Playwright fallback...")
        try:
            products = asyncio.run(_scrape_with_playwright(DEPOP_USERNAME))
        except Exception as exc:  # pragma: no cover - runtime only
            print(f"Playwright fallback failed: {exc}")

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
