import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE = "https://www.supremevalues.com/mm2/"
CATEGORIES = [
    "sets",
    "uniques",
    "evos",
    "ancients",
    "vintages",
    "chromas",
    "godlies",
    "legendaries",
    "rares",
    "uncommons",
    "commons",
    "pets",
    "misc"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (MM2 Supreme Trade Calculator)"
}

os.makedirs("data", exist_ok=True)


def number(value):
    if not value:
        return None

    value = value.replace(",", "").strip()

    match = re.search(r"-?\d+(?:\.\d+)?", value)
    if not match:
        return None

    n = float(match.group())

    return int(n) if n.is_integer() else n


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def clean(text):
    return " ".join(text.split())


items = {}

for category in CATEGORIES:
    url = BASE + category + ".php"

    try:
        soup = get_page(url)

        for element in soup.find_all(["tr", "div", "article"]):
            text = clean(element.get_text(" ", strip=True))

            if not text:
                continue

            value_match = re.search(
                r"\bValue\s*[:\-]?\s*([0-9,.]+)",
                text,
                re.I
            )

            if not value_match:
                continue

            name = None

            link = element.find("a")

            if link:
                name = clean(link.get_text(" ", strip=True))

            if not name:
                continue

            value = number(value_match.group(1))

            if value is None:
                continue

            item = {
                "name": name,
                "value": value,
                "category": category
            }

            range_match = re.search(
                r"\bRange\s*[:\-]?\s*([0-9,.]+)\s*[-–]\s*([0-9,.]+)",
                text,
                re.I
            )

            if range_match:
                item["range"] = {
                    "low": number(range_match.group(1)),
                    "high": number(range_match.group(2))
                }

            demand_match = re.search(
                r"\bDemand\s*[:\-]?\s*([A-Za-z0-9 +\-]+)",
                text,
                re.I
            )

            if demand_match:
                item["demand"] = clean(demand_match.group(1))

            stability_match = re.search(
                r"\bStability\s*[:\-]?\s*([A-Za-z0-9 +\-]+)",
                text,
                re.I
            )

            if stability_match:
                item["stability"] = clean(stability_match.group(1))

            rarity_match = re.search(
                r"\bRarity\s*[:\-]?\s*([A-Za-z0-9 +\-]+)",
                text,
                re.I
            )

            if rarity_match:
                item["rarity"] = clean(rarity_match.group(1))

            key = name.lower()

            if key not in items:
                items[key] = item

        print(f"Updated {category}")

    except Exception as error:
        print(f"Failed {category}: {error}")

    time.sleep(1)


output = {
    "source": "Supreme Values",
    "source_url": "https://www.supremevalues.com/",
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "item_count": len(items),
    "items": sorted(
        items.values(),
        key=lambda x: x["name"].lower()
    )
}

with open("data/values.json", "w", encoding="utf-8") as file:
    json.dump(
        output,
        file,
        indent=2,
        ensure_ascii=False
    )

print(f"Saved {len(items)} items.")
