#!/usr/bin/env python3
"""
Stage 1: Fetch top 50 articles for ALL 337 languages from mdwiki API.
Saves results incrementally to avoid data loss on timeout.
"""
import urllib.request
import json
import time
import os

WORK_DIR = "/sessions/modest-compassionate-cray"
CHECKPOINT_FILE = os.path.join(WORK_DIR, "all_langs_top50.json")
PROGRESS_FILE = os.path.join(WORK_DIR, "fetch_progress.json")

def get_all_languages():
    url = 'https://mdwiki.toolforge.org/views/api.php?sub_dir=users-agents'
    req = urllib.request.Request(url, headers={'User-Agent': 'WikiMedAnalysis/1.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.loads(response.read().decode('utf-8'))
    langs = []
    for item in data['data']:
        if not item['is_summary']:
            langs.append({'lang': item['lang'], 'titles': item['titles'], 'total': item['total']})
    langs.sort(key=lambda x: x['total'], reverse=True)
    return langs

def fetch_top_articles(lang, num_titles, top_n=50):
    """Fetch articles for a language. Uses batching for large datasets."""
    all_records = []
    batch_size = min(10000, max(num_titles + 100, 500))
    start = 0

    while True:
        url = f'https://mdwiki.toolforge.org/views/api.php?lang={lang}&sub_dir=users-agents&start={start}&length={batch_size}'
        req = urllib.request.Request(url, headers={'User-Agent': 'WikiMedAnalysis/1.0'})

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode('utf-8'))
        except Exception as e:
            # Retry with smaller batch
            if batch_size > 1000:
                batch_size = batch_size // 2
                continue
            else:
                print(f"    FAILED: {e}")
                return []

        total_records = data.get('recordsTotal', 0)
        batch = [r for r in data['data'] if not r.get('is_summary', False)]
        all_records.extend(batch)

        start += batch_size
        if start >= total_records:
            break
        time.sleep(0.2)

    all_records.sort(key=lambda x: x.get('total', 0), reverse=True)
    return all_records[:top_n]

if __name__ == '__main__':
    print("Fetching language list...")
    all_langs = get_all_languages()
    print(f"Total languages: {len(all_langs)}")

    # Load checkpoint if exists
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE) as f:
            results = json.load(f)
        print(f"Resuming from checkpoint: {len(results)} languages already done")
    else:
        results = {}

    done_count = len(results)
    total = len(all_langs)

    for i, lang_info in enumerate(all_langs):
        lang = lang_info['lang']
        if lang in results:
            continue

        num_titles = lang_info['titles']
        if num_titles == 0:
            results[lang] = []
            continue

        print(f"[{done_count+1}/{total}] {lang} ({num_titles} articles, {lang_info['total']:,} views)...", end=' ', flush=True)

        articles = fetch_top_articles(lang, num_titles)

        # Store compact form
        results[lang] = [
            {'title': a['title'], 'total': a.get('total', 0)}
            for a in articles
        ]

        done_count += 1

        if articles:
            print(f"got {len(articles)} (top: {articles[0]['title'][:40]})")
        else:
            print("no data")

        # Checkpoint every 20 languages
        if done_count % 20 == 0:
            with open(CHECKPOINT_FILE, 'w') as f:
                json.dump(results, f, ensure_ascii=False)
            print(f"  --- Checkpoint saved: {done_count}/{total} ---")

        time.sleep(0.15)

    # Final save
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(results, f, ensure_ascii=False)

    # Stats
    non_empty = sum(1 for v in results.values() if v)
    print(f"\n{'='*60}")
    print(f"DONE: {len(results)} languages fetched, {non_empty} with data")
    print(f"Saved to {CHECKPOINT_FILE}")
