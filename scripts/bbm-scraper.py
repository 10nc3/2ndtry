#!/usr/bin/env python3
"""
BBM Pertamina Price Scraper
Fetches corporate diesel prices from Kompas Money articles.
Focus: Sumatera zones — Dexlite, Pertamina Dex, Bio Solar.

Behavior:
  - Silent (no output) if no price changes from baseline
  - Prints brief only when prices changed
  - Exit 0 always
"""

import urllib.request
import urllib.error
import json
import re
import os
import sys
from datetime import datetime, timezone, timedelta

# ── Configuration ──
BASELINE_PATH = os.path.expanduser("~/.hermes/workspace/bbm-baseline.json")
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
JAKARTA_TZ = timezone(timedelta(hours=7))

# Kompas article — "daftar lengkap" format with <ul><li> price lists
SOURCE_URL = (
    "https://money.kompas.com/read/2026/05/21/081100226/"
    "cek-harga-dexlite-hari-ini-21-mei-2026-di-spbu-se-indonesia-ini-daftar-lengkap"
)

# Zone → group mapping (Kompas <li> uses short names like "Aceh", not "Sumatera Aceh")
ZONE_TO_GROUP = {
    "aceh": "Sumatera-Group-A",
    "sumatera utara": "Sumatera-Group-A",
    "jambi": "Sumatera-Group-A",
    "bengkulu": "Sumatera-Group-A",
    "sumatera selatan": "Sumatera-Group-A",
    "bangka belitung": "Sumatera-Group-A",
    "lampung": "Sumatera-Group-A",
    "sumatera barat": "Sumatera-Group-B",
    "riau": "Sumatera-Group-B",
    "kepulauan riau": "Sumatera-Group-B",
    "sabang": "FTZ-Sabang",
    "ftz sabang": "FTZ-Sabang",
    "batam": "FTZ-Batam",
    "ftz batam": "FTZ-Batam",
}

GROUP_ZONES = {
    "Sumatera-Group-A": ["Aceh", "Sumatera Utara", "Jambi", "Bengkulu", "Sumatera Selatan", "Bangka Belitung", "Lampung"],
    "Sumatera-Group-B": ["Sumatera Barat", "Riau", "Kepulauan Riau"],
    "FTZ-Sabang": ["Sabang"],
    "FTZ-Batam": ["Batam"],
}

# ── Fetch ──

def fetch_url(url, timeout=15):
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


# ── Extract ──

def extract_article_body(html):
    """Isolate Kompas article body from surrounding nav/widgets."""
    # Primary: read__content div
    m = re.search(r'<div[^>]*class="read__content"[^>]*>(.*?)</div>\s*<div[^>]*class="read__sidebar"', html, re.DOTALL)
    if m:
        return m.group(1)
    # Fallback: any read__content
    m = re.search(r'<div[^>]*class="read__content"[^>]*>(.*?)</div>', html, re.DOTALL)
    if m:
        return m.group(1)
    return html


def extract_dexlite_prices(html):
    """
    Extract zone→Dexlite price from Kompas <ul><li> lists.
    Returns dict: {group_name: {"Dexlite": int_price}}
    """
    prices = {}

    # Find all <ul> blocks, then extract <li> items from each
    ul_blocks = re.findall(r'<ul[^>]*>(.*?)</ul>', html, re.DOTALL | re.IGNORECASE)

    for ul in ul_blocks:
        # Skip <ul> blocks without price patterns (nav menus, etc.)
        if 'Rp' not in ul or 'per liter' not in ul:
            continue

        li_items = re.findall(r'<li[^>]*>(.*?)</li>', ul, re.DOTALL | re.IGNORECASE)
        for li in li_items:
            # Strip inner HTML (links, spans, etc.)
            clean = re.sub(r'<[^>]+>', '', li).strip()

            # Match: Zone: Rp X.XXX per liter
            m = re.match(r'^([^:]+):\s*Rp\s*([0-9.,]+)\s*per liter$', clean, re.IGNORECASE)
            if not m:
                continue

            zone_raw = m.group(1).strip()
            price_str = m.group(2).replace(".", "").replace(",", "")

            try:
                price = int(price_str)
            except ValueError:
                continue

            zone_key = zone_raw.lower()
            group = ZONE_TO_GROUP.get(zone_key)
            if group and group not in prices:
                prices[group] = {"Dexlite": price}

    return prices


# ── Baseline ──

def load_baseline():
    if not os.path.exists(BASELINE_PATH):
        return None
    with open(BASELINE_PATH, "r") as f:
        return json.load(f)


def save_baseline(baseline):
    os.makedirs(os.path.dirname(BASELINE_PATH), exist_ok=True)
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)


# ── Merge & Compare ──

def merge_with_baseline(fresh, baseline):
    """
    fresh: {group: {"Dexlite": price}} from scraper
    baseline: full baseline dict with lastBbmPrices

    Returns merged {group: {fuel: price}} and list of changes.
    """
    if not baseline or "lastBbmPrices" not in baseline:
        return fresh, []

    merged = {}
    changes = []
    baseline_prices = baseline["lastBbmPrices"]

    all_groups = set(baseline_prices.keys()) | set(fresh.keys())

    for group in all_groups:
        group_base = baseline_prices.get(group, {})
        group_fresh = fresh.get(group, {})

        merged[group] = {}
        for fuel in ["Dexlite", "Pertamina Dex", "Bio Solar"]:
            old_price = group_base.get(fuel)
            new_price = group_fresh.get(fuel)

            if new_price is not None:
                merged[group][fuel] = new_price
                if old_price is not None and old_price != new_price:
                    changes.append({
                        "group": group,
                        "fuel": fuel,
                        "old": old_price,
                        "new": new_price,
                    })
                elif old_price is None:
                    changes.append({
                        "group": group,
                        "fuel": fuel,
                        "old": None,
                        "new": new_price,
                        "note": "new",
                    })
            else:
                # Carry forward from baseline
                if old_price is not None:
                    merged[group][fuel] = old_price

    return merged, changes


def format_brief(changes, merged, source_url, now):
    """Format a Discord-friendly brief. Only includes changed groups."""
    lines = []
    lines.append(f"🜁 BBM Alert — {now.strftime('%d %b %Y')}")
    lines.append("")

    changed_groups = {c["group"] for c in changes}
    for group in sorted(changed_groups):
        lines.append(f"**{group}**")
        for fuel in ["Dexlite", "Pertamina Dex", "Bio Solar"]:
            price = merged[group].get(fuel)
            if price is None:
                continue
            # Check if this specific fuel changed
            ch = next((c for c in changes if c["group"] == group and c["fuel"] == fuel), None)
            if ch:
                if ch.get("note") == "new":
                    lines.append(f"• {fuel}: Rp {price:,} *(new)*")
                else:
                    lines.append(f"• {fuel}: Rp {ch['old']:,} → **Rp {price:,}**")
            else:
                lines.append(f"• {fuel}: Rp {price:,}")
        lines.append("")

    lines.append(f"Source: [Kompas Money]({source_url})")
    lines.append(f"Checked: {now.strftime('%H:%M')} BKK")
    return "\n".join(lines)


# ── Main ──

def main():
    now = datetime.now(JAKARTA_TZ)

    html = fetch_url(SOURCE_URL)
    if html.startswith("ERROR:") or html.startswith("HTTP_ERROR:"):
        # Silent failure — don't spam on source errors
        return 0

    fresh = extract_dexlite_prices(html)
    if not fresh:
        return 0

    baseline = load_baseline()
    merged, changes = merge_with_baseline(fresh, baseline)

    if not changes:
        # No changes — silent exit
        return 0

    # Build new baseline
    new_baseline = {
        "focusZones": ["Sumatera"],
        "lastNotifiedAt": now.isoformat(),
        "lastUpdated": now.isoformat(),
        "source": "kompas-money-dexlite",
        "sourceUrl": SOURCE_URL,
        "lastBbmCheckDate": now.strftime("%Y-%m-%d"),
        "lastBbmPrices": merged,
    }
    save_baseline(new_baseline)

    # Output brief for cron delivery
    brief = format_brief(changes, merged, SOURCE_URL, now)
    print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
