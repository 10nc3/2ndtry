#!/usr/bin/env python3
"""
CPO / KPBN Price Scraper
Fetches palm oil prices from public sources.
Focus: KPBN tender, Bursa Malaysia FCPO, domestic references.
"""

import urllib.request
import urllib.error
import json
import re
import os
from datetime import datetime

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

SOURCES = [
    {
        "name": "tradingeconomics-cpo",
        "url": "https://tradingeconomics.com/commodity/palm-oil",
        "type": "html",
    },
    {
        "name": "kpbn-home",
        "url": "https://www.kpbn.co.id/",
        "type": "html",
    },
    {
        "name": "kpbn-pricing",
        "url": "https://www.kpbn.co.id/memberarea/pricing",
        "type": "html",
    },
    {
        "name": "bursamalaysia-fcpo",
        "url": "https://www.bursamalaysia.com/market_information/derivatives_prices?product=FCPO",
        "type": "html",
    },
]

def fetch_url(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.google.com/",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"HTTP_ERROR:{e.code}"
    except Exception as e:
        return f"ERROR:{e}"

def extract_tradingeconomics(html):
    """Extract CPO price from TradingEconomics."""
    # Look for: "Palm Oil fell to 4,473 MYR/T on May 25, 2026"
    match = re.search(r'Palm Oil fell to ([0-9,]+) MYR/T on ([^,]+)', html)
    if match:
        price = match.group(1).replace(",", "")
        date_str = match.group(2).strip()
        return {"price_myr": int(price), "date": date_str, "change_pct": None}
    
    # Try alternate pattern: "Palm Oil - values, historical data"
    # Look for last price in JSON-like data
    last_match = re.search(r'"last":([0-9.]+)', html)
    if last_match:
        return {"price_myr": float(last_match.group(1)), "date": None, "change_pct": None}
    
    return None

def extract_kpbn(html):
    """Extract any price info from KPBN pages."""
    results = {}
    
    # Check if member-only
    if "memberarea" in html or "login" in html.lower() or "Membership" in html:
        results["access"] = "member_only"
    
    # Look for any Rp prices
    rp_matches = re.findall(r'Rp\.?\s*([0-9.,]+)', html)
    if rp_matches:
        results["rp_prices"] = rp_matches[:10]
    
    # Look for CPO mentions with nearby prices
    cpo_context = re.findall(r'.{0,80}CPO.{0,80}', html, re.IGNORECASE)
    if cpo_context:
        results["cpo_contexts"] = cpo_context[:5]
    
    return results if results else None

def extract_bursamalaysia(html):
    """Extract FCPO prices from Bursa Malaysia."""
    if "cloudflare" in html.lower() or "challenge" in html.lower():
        return {"access": "blocked_by_cloudflare"}
    
    # Look for price tables
    prices = []
    # Try to find FCPO contract prices
    price_rows = re.findall(r'FCPO[A-Z0-9]+[^0-9]*([0-9,]+\.?[0-9]*)', html)
    if price_rows:
        prices = price_rows[:10]
    
    return {"prices": prices} if prices else None

def main():
    print(f"🜁 CPO/KPBN Scraper — {datetime.now().isoformat()}")
    print("=" * 50)
    
    for source in SOURCES:
        print(f"\n📡 Source: {source['name']}")
        print(f"   URL: {source['url']}")
        
        html = fetch_url(source['url'])
        if html.startswith("ERROR:") or html.startswith("HTTP_ERROR:"):
            print(f"   ❌ {html}")
            continue
        
        print(f"   ✅ Fetched {len(html)} chars")
        
        if source['name'] == "tradingeconomics-cpo":
            data = extract_tradingeconomics(html)
            if data:
                print(f"   📊 CPO: {data['price_myr']} MYR/ton")
                if data['date']:
                    print(f"   📅 Date: {data['date']}")
            else:
                print("   ⚠️  No price data found")
        
        elif source['name'].startswith("kpbn"):
            data = extract_kpbn(html)
            if data:
                for k, v in data.items():
                    print(f"   📋 {k}: {v}")
            else:
                print("   ⚠️  No data extracted")
        
        elif source['name'] == "bursamalaysia-fcpo":
            data = extract_bursamalaysia(html)
            if data:
                for k, v in data.items():
                    print(f"   📋 {k}: {v}")
            else:
                print("   ⚠️  No data extracted")

if __name__ == "__main__":
    exit(main())
