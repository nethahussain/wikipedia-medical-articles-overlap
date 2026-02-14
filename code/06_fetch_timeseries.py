#!/usr/bin/env python3
"""
Fetch year-by-year pageview data (2016-2025) for key languages and their top articles.
Also fetch aggregate yearly totals per language.
"""

import json, os, time, urllib.request

WORK_DIR = "/sessions/modest-compassionate-cray"
YEARS = [str(y) for y in range(2016, 2026)]
UA = {'User-Agent': 'WikiMedAnalysis/1.0'}

# ── Stage 1: Language-level yearly totals ──
print("Fetching language-level yearly totals...")
url = 'https://mdwiki.toolforge.org/views/api.php?sub_dir=users-agents'
req = urllib.request.Request(url, headers=UA)
with urllib.request.urlopen(req, timeout=60) as resp:
    lang_meta = json.loads(resp.read().decode('utf-8'))

lang_yearly = {}
for item in lang_meta['data']:
    if not item['is_summary']:
        lang_yearly[item['lang']] = {
            'titles': item['titles'],
            'yearly': {y: item.get(y, 0) for y in YEARS},
            'total': item['total']
        }

print(f"  Got yearly data for {len(lang_yearly)} languages")

# ── Stage 2: Article-level yearly data for selected languages ──
# Focus on a diverse set of important languages
TARGET_LANGS = ['en', 'es', 'de', 'fr', 'ru', 'ja', 'pt', 'zh', 'ar', 'hi',
                'id', 'vi', 'tr', 'fa', 'ko', 'pl', 'nl', 'sv', 'uk', 'th',
                'bn', 'ta', 'sw', 'simple']

# Load our Wikidata mapping
with open(os.path.join(WORK_DIR, "all_wikidata.json")) as f:
    all_wikidata = json.load(f)

article_timeseries = {}  # lang -> {title -> {year -> views}}

for lang in TARGET_LANGS:
    print(f"  Fetching articles for {lang}...")
    try:
        # Fetch top 50 articles with yearly breakdown
        api_url = f'https://mdwiki.toolforge.org/views/api.php?lang={lang}&sub_dir=users-agents&start=0&length=50'
        req = urllib.request.Request(api_url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode('utf-8'))

        lang_articles = {}
        for item in data['data']:
            if item.get('is_summary'):
                continue
            title = item['title']
            yearly = {y: item.get(y, 0) for y in YEARS}
            lang_articles[title] = yearly

        article_timeseries[lang] = lang_articles
        print(f"    Got {len(lang_articles)} articles")
    except Exception as e:
        print(f"    ERROR: {e}")
        # Try smaller batch for English
        if lang == 'en':
            print("    Retrying English in smaller batches...")
            lang_articles = {}
            for start in range(0, 60, 10):
                try:
                    api_url = f'https://mdwiki.toolforge.org/views/api.php?lang=en&sub_dir=users-agents&start={start}&length=10'
                    req = urllib.request.Request(api_url, headers=UA)
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                    for item in data['data']:
                        if not item.get('is_summary'):
                            lang_articles[item['title']] = {y: item.get(y, 0) for y in YEARS}
                except Exception as e2:
                    print(f"      batch {start}: {e2}")
                time.sleep(0.5)
            article_timeseries['en'] = lang_articles
            print(f"    Got {len(lang_articles)} English articles")

    time.sleep(0.3)

# ── Save ──
output = {
    'years': YEARS,
    'lang_yearly': lang_yearly,
    'article_timeseries': article_timeseries
}

with open(os.path.join(WORK_DIR, "timeseries_data.json"), 'w') as f:
    json.dump(output, f, ensure_ascii=False)

print(f"\nSaved timeseries data:")
print(f"  Language yearly totals: {len(lang_yearly)}")
print(f"  Article timeseries: {len(article_timeseries)} languages")
print("Done.")
