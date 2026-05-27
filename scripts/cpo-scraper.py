#!/usr/bin/env python3
"""
CPO Price Scraper
Fetches Crude Palm Oil prices from public sources.
Sources:
  - KPBN tender (domestic Indonesia) via palmoilmagazine.com
  - Bursa Malaysia FCPO (international benchmark) via TradingEconomics
"""

import urllib.request
import urllib.error
import json
import re
import os
from datetime import datetime, timezone, timedelta

# ── Configuration ──
BASELINE_PATH = os.path.expanduser("~/.hermes/workspace/cpo-baseline.json")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
JAKARTA_TZ = timezone(timedelta(hours=7))

SOURCES = [
    {
        "name": "palmoilmagazine-kpbn",
        "url": "https://www.palmoilmagazine.com/cpo-price",
        "type": "html",
    },
    {
        "name": "tradingeconomics-bursa",
        "url": "https://tradingeconomics.com/commodity/palm-oil",
        "type": "html",
    },
]

MONTH_MAP = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}


# ── Fetch ──

def fetch_url(url, timeout=15):
    """Fetch URL with proper headers."""
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"HTTP_ERROR:{e.code}"
    except Exception as e:
        return f"ERROR:{e}"


# ── Extract: Palm Oil Magazine (KPBN) ──

def parse_date_from_headline(headline, default_year=None):
    """Extract date from headline like 'on Monday (May 25)' or 'on May 20'."""
    if default_year is None:
        default_year = datetime.now(JAKARTA_TZ).year

    patterns = [
        r'\(\s*([A-Za-z]+)\s+(\d{1,2})\s*\)',  # (May 25)
        r'\bon\s+([A-Za-z]+)\s+(\d{1,2})\b',    # on May 20
        r'\b([A-Za-z]+)\s+(\d{1,2}),?\s+\d{4}\b',  # May 20, 2026
    ]

    for pat in patterns:
        m = re.search(pat, headline)
        if m:
            month_name = m.group(1).lower()
            day = m.group(2).zfill(2)
            month_num = MONTH_MAP.get(month_name, "00")
            if month_num != "00":
                year_match = re.search(r'\b(\d{4})\b', m.group(0))
                year = year_match.group(1) if year_match else str(default_year)
                return f"{year}-{month_num}-{day}"

    return None


def extract_kpbn_from_palmoilmagazine(html):
    """
    Extract KPBN tender prices from Palm Oil Magazine CPO price page.
    Matches article <a> tags (href contains /cpo-price/YYYY/MM/DD/) and
    extracts price + date from title attribute.
    """
    prices = []

    article_pattern = re.compile(
        r'<a[^>]*href="https://www\.palmoilmagazine\.com/cpo-price/(\d{4}/\d{2}/\d{2})/[^"]*"[^>]*title="([^"]*KPBN[^"]*)"',
        re.IGNORECASE,
    )

    for match in article_pattern.finditer(html):
        url_date = match.group(1).replace("/", "-")
        title = match.group(2)

        price_match = re.search(r'IDR\s*([0-9,.]+)\s*/?[Kk]g', title)
        if not price_match:
            continue

        price_str = price_match.group(1).replace(",", "").replace(".", "")
        try:
            price = int(price_str)
        except ValueError:
            continue

        headline_date = parse_date_from_headline(title)
        date_str = headline_date or url_date

        direction = "neutral"
        title_lower = title.lower()
        if any(w in title_lower for w in ["plunge", "fall", "drop", "weaken", "decline", "fell"]):
            direction = "down"
        elif any(w in title_lower for w in ["rise", "up", "gain", "strengthen", "rebound", "rally"]):
            direction = "up"
        elif "withdrawn" in title_lower or "remains" in title_lower or "stable" in title_lower:
            direction = "unchanged"

        prices.append({
            "source": "palmoilmagazine",
            "type": "kpbn_tender",
            "date": date_str,
            "price_idr_per_kg": price,
            "headline": title.strip(),
            "direction": direction,
        })

    # Deduplicate by (date, price)
    seen = set()
    unique = []
    for p in prices:
        key = (p["date"], p["price_idr_per_kg"])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique


# ── Extract: TradingEconomics (Bursa Malaysia) ──

def extract_bursa_from_tradingeconomics(html):
    """Extract Bursa Malaysia CPO benchmark from TradingEconomics."""
    prices = []
    seen = set()

    te_pattern = re.compile(
        r'Palm Oil\s+(?:fell|rose|increased|decreased|traded|was)\s+(?:to|at)\s+([0-9,.]+)\s+MYR/T\s+on\s+([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
        re.IGNORECASE,
    )

    for match in te_pattern.finditer(html):
        price_str = match.group(1)
        month_name = match.group(2)
        day = match.group(3)
        year = match.group(4)

        price_clean = price_str.replace(",", "").replace(".", "")
        try:
            price = int(price_clean)
        except ValueError:
            continue

        month_num = MONTH_MAP.get(month_name.lower(), "00")
        date_str = f"{year}-{month_num}-{day.zfill(2)}"

        direction = "neutral"
        action = match.group(0).lower()
        if "fell" in action or "decreased" in action:
            direction = "down"
        elif "rose" in action or "increased" in action:
            direction = "up"

        key = (date_str, price)
        if key not in seen:
            seen.add(key)
            prices.append({
                "source": "tradingeconomics",
                "type": "bursa_malaysia_fcpo",
                "date": date_str,
                "price_myr_per_ton": price,
                "direction": direction,
                "raw": match.group(0),
            })

    # Fallback: meta description
    if not prices:
        meta_pattern = re.compile(
            r'<meta[^>]*description[^>]*content="([^"]*Palm Oil[^"]*)"',
            re.IGNORECASE,
        )
        meta_match = meta_pattern.search(html)
        if meta_match:
            meta = meta_match.group(1)
            price_m = re.search(r'([0-9,.]+)\s*MYR/T', meta)
            if price_m:
                price_str = price_m.group(1).replace(",", "").replace(".", "")
                try:
                    price = int(price_str)
                    prices.append({
                        "source": "tradingeconomics",
                        "type": "bursa_malaysia_fcpo",
                        "date": datetime.now(JAKARTA_TZ).strftime("%Y-%m-%d"),
                        "price_myr_per_ton": price,
                        "direction": "unknown",
                        "raw": meta,
                    })
                except ValueError:
                    pass

    return prices


# ── Aggregate ──

def get_current_prices():
    """Fetch and parse current CPO prices from all sources."""
    all_prices = []
    errors = []

    for source in SOURCES:
        html = fetch_url(source["url"])
        if html.startswith("ERROR:") or html.startswith("HTTP_ERROR:"):
            errors.append(f"{source['name']}: {html}")
            continue

        if source["name"] == "palmoilmagazine-kpbn":
            prices = extract_kpbn_from_palmoilmagazine(html)
        elif source["name"] == "tradingeconomics-bursa":
            prices = extract_bursa_from_tradingeconomics(html)
        else:
            prices = []

        all_prices.extend(prices)

    return all_prices, errors


# ── Baseline Management ──

def load_baseline():
    """Load the current baseline from disk."""
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def save_baseline(baseline):
    """Save baseline to disk."""
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)


# ── Comparison ──

def compare_with_baseline(current_prices, baseline):
    """Compare current prices with baseline. Returns changes dict."""
    if not baseline or "lastPrices" not in baseline:
        return {"status": "no_baseline", "changes": []}

    changes = []
    baseline_prices = baseline["lastPrices"]

    baseline_idx = {}
    for bp in baseline_prices:
        key = (bp.get("source"), bp.get("type"), bp.get("date"))
        baseline_idx[key] = bp

    for cp in current_prices:
        key = (cp.get("source"), cp.get("type"), cp.get("date"))
        if key not in baseline_idx:
            changes.append({"status": "new", "price": cp})
            continue

        bp = baseline_idx[key]
        cp_price = cp.get("price_idr_per_kg") or cp.get("price_myr_per_ton")
        bp_price = bp.get("price_idr_per_kg") or bp.get("price_myr_per_ton")

        if cp_price != bp_price:
            changes.append({
                "status": "changed",
                "source": cp["source"],
                "type": cp["type"],
                "date": cp["date"],
                "old": bp_price,
                "new": cp_price,
            })

    return {"status": "compared", "changes": changes}


# ── Main ──

def main():
    now = datetime.now(JAKARTA_TZ)
    print(f"🌴 CPO Scraper — {now.isoformat()}")
    print("=" * 50)

    prices, errors = get_current_prices()

    if errors:
        print("\n⚠️  Errors:")
        for err in errors:
            print(f"  - {err}")

    if not prices:
        print("\n❌ No prices fetched from any source")
        return 1

    print(f"\n📊 Fetched {len(prices)} price entries:")
    for p in prices:
        if "price_idr_per_kg" in p:
            print(f"  [{p['source']}] {p['type']} @ {p['date']}: IDR {p['price_idr_per_kg']:,}/kg ({p['direction']})")
        elif "price_myr_per_ton" in p:
            print(f"  [{p['source']}] {p['type']} @ {p['date']}: {p['price_myr_per_ton']:,} MYR/ton ({p['direction']})")

    baseline = load_baseline()
    if baseline:
        print(f"\n📁 Baseline loaded: {baseline.get('lastCheckDate', 'unknown')}")
        comparison = compare_with_baseline(prices, baseline)
        if comparison["changes"]:
            print(f"\n🔄 Changes detected ({len(comparison['changes'])}):")
            for ch in comparison["changes"]:
                if ch["status"] == "new":
                    p = ch["price"]
                    price_val = p.get("price_idr_per_kg") or p.get("price_myr_per_ton")
                    unit = "IDR/kg" if "price_idr_per_kg" in p else "MYR/ton"
                    print(f"  + NEW: {p['source']} {p['type']} @ {p['date']} = {price_val:,} {unit}")
                else:
                    print(f"  ~ CHANGED: {ch['source']} {ch['type']} @ {ch['date']}: {ch['old']:,} → {ch['new']:,}")
        else:
            print("\n✅ No changes from baseline")
    else:
        print("\n⚠️  No baseline found — will create one")

    new_baseline = {
        "lastCheckDate": now.strftime("%Y-%m-%d"),
        "lastCheckTime": now.isoformat(),
        "lastPrices": prices,
    }
    save_baseline(new_baseline)
    print(f"\n💾 Baseline saved to {BASELINE_PATH}")

    return 0


if __name__ == "__main__":
    exit(main())
