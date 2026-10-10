import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.supremevalues.com/mm2/"
CATEGORIES = [
    "sets", "uniques", "evos", "ancients", "vintages",
    "chromas", "godlies", "legendaries", "rares",
    "uncommons", "commons", "pets", "misc", "untradables"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
}


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def get_value(text):
    match = re.search(
        r"\bValue\s*[-:]\s*([0-9][0-9,.]*)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return float(match.group(1).replace(",", ""))


def scrape_category(category):
    # Try both URL formats in case Supreme changes its routes.
    urls = [
        BASE_URL + category,
        BASE_URL + category + ".php"
    ]

    soup = None

    for url in urls:
        try:
            print("Checking:", url)
            candidate = get_page(url)

            if candidate.find("img") or candidate.find("table"):
                soup = candidate
                break

        except Exception as error:
            print("Page failed:", error)

    if soup is None:
        print("Could not load:", category)
        return []

    results = {}

    for element in soup.find_all(["tr", "article", "div", "li"]):
        text = clean(element.get_text(" ", strip=True))

        if len(text) > 2000:
            continue

        value = get_value(text)

        if value is None:
            continue

        name = None

        # Item images commonly contain the item name in their alt text.
        for img in element.find_all("img"):
            alt = clean(img.get("alt", ""))

            if (
                alt
                and alt.lower() not in {
                    "image",
                    "supreme values",
                    "item stability"
                }
                and len(alt) <= 100
            ):
                name = alt
                break

        # Try headings and links if no useful image name exists.
        if not name:
            for selector in ["h1", "h2", "h3", "h4", "a"]:
                found = element.select_one(selector)

                if found:
                    candidate = clean(
                        found.get_text(" ", strip=True)
                    )

                    if candidate and len(candidate) <= 100:
                        name = candidate
                        break

        if not name:
            continue

        key = name.casefold()

        results.setdefault(
            key,
            {
                "name": name,
                "value": int(value) if value.is_integer() else value,
                "category": category
            }
        )

    print(f"{category}: {len(results)} items")
    return list(results.values())


def main():
    items = {}

    for category in CATEGORIES:
        try:
            for item in scrape_category(category):
                items.setdefault(
                    item["name"].casefold(),
                    item
                )
        except Exception as error:
            print("Category error:", category, error)

        time.sleep(1)

    # Never replace the data file with an empty result.
    if not items:
        raise RuntimeError(
            "ZERO ITEMS FOUND. Existing values.json was not overwritten."
        )

    output = {
        "source": "Supreme Values",
        "source_url": "https://www.supremevalues.com/",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "item_count": len(items),
        "items": sorted(
            items.values(),
            key=lambda item: item["name"].casefold()
        )
    }

    os.makedirs("data", exist_ok=True)

    with open(
        "data/values.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print("TOTAL ITEMS SAVED:", len(items))


if __name__ == "__main__":
    main()
