import json
import os
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.supremevalues.com/mm2/"
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
    "misc",
    "untradables",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 10) "
        "AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36"
    )
}


def clean(value):
    return re.sub(r"\s+", " ", str(value)).strip()


def number(value):
    if value is None:
        return None

    value = clean(value).replace(",", "")

    match = re.search(r"-?\d+(?:\.\d+)?", value)

    if not match:
        return None

    result = float(match.group(0))

    if result.is_integer():
        return int(result)

    return result


def get_soup(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "html.parser"
    )


def extract_label(text, label):
    pattern = rf"{re.escape(label)}\s*[-:]\s*(.*?)(?=\s+(?:Value|Range|Stability|Demand|Rarity|Origin|Change in Value|Aliases|Flippability|Chance of Rising)\s*[-:]|$)"

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return clean(match.group(1))


def extract_value(text):
    match = re.search(
        r"\bValue\s*[-:]\s*([0-9,.]+)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    return number(match.group(1))


def extract_range(text):
    match = re.search(
        r"\bRange\s*[-:]\s*(.*?)(?=\s+(?:Stability|Demand|Rarity|Origin|Change in Value|Aliases|Flippability|Chance of Rising)\s*[-:]|$)",
        text,
        re.IGNORECASE
    )

    if not match:
        return None

    value = clean(match.group(1))

    if value.lower() in ("n/a", "na", "none"):
        return None

    numbers = re.findall(
        r"[0-9,.]+",
        value
    )

    if len(numbers) >= 2:
        return {
            "low": number(numbers[0]),
            "high": number(numbers[1])
        }

    return {
        "text": value
    }


def find_item_name(element):
    for selector in [
        "h1",
        "h2",
        "h3",
        "h4",
        ".item-name",
        ".name",
        "a"
    ]:
        found = element.select_one(selector)

        if found:
            name = clean(found.get_text(" ", strip=True))

            if name and len(name) <= 100:
                return name

    return None


def parse_category(category):
    url = BASE_URL + category + ".php"

    print(f"Downloading {url}")

    try:
        soup = get_soup(url)
    except Exception as error:
        print(f"ERROR loading {category}: {error}")
        return []

    results = []

    containers = soup.select(
        "tr, .item, .item-card, .card, article, .value-item"
    )

    seen = set()

    for element in containers:
        text = clean(
            element.get_text(
                " ",
                strip=True
            )
        )

        if "Value" not in text:
            continue

        value = extract_value(text)

        if value is None:
            continue

        name = find_item_name(element)

        if not name:
            continue

        lowered = name.lower()

        if lowered in seen:
            continue

        seen.add(lowered)

        item = {
            "name": name,
            "value": value,
            "category": category
        }

        item_range = extract_range(text)

        if item_range is not None:
            item["range"] = item_range

        demand = extract_label(text, "Demand")

        if demand:
            item["demand"] = demand

        stability = extract_label(text, "Stability")

        if stability:
            item["stability"] = stability

        rarity = extract_label(text, "Rarity")

        if rarity:
            item["rarity"] = rarity

        origin = extract_label(text, "Origin")

        if origin:
            item["origin"] = origin

        change = extract_label(
            text,
            "Change in Value"
        )

        if change:
            item["change"] = change

        aliases = extract_label(
            text,
            "Aliases"
        )

        if aliases:
            item["aliases"] = aliases

        results.append(item)

    print(
        f"{category}: {len(results)} items found"
    )

    return results


def main():
    all_items = {}

    for category in CATEGORIES:
        try:
            items = parse_category(category)

            for item in items:
                key = item["name"].strip().lower()

                if key not in all_items:
                    all_items[key] = item

        except Exception as error:
            print(
                f"ERROR processing {category}: {error}"
            )

        time.sleep(1)

    output = {
        "source": "Supreme Values",
        "source_url": "https://www.supremevalues.com/",
        "updated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "item_count": len(all_items),
        "items": sorted(
            all_items.values(),
            key=lambda item:
                item["name"].lower()
        )
    }

    os.makedirs(
        "data",
        exist_ok=True
    )

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

    print()
    print(
        f"TOTAL ITEMS SAVED: {len(all_items)}"
    )
    print(
        "Created: data/values.json"
    )


if __name__ == "__main__":
    main()
