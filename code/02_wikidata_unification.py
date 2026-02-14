#!/usr/bin/env python3
"""
Stage 2: Query Wikidata for ALL languages to unify article titles.
Processes in batches with checkpointing.
"""
import urllib.request
import urllib.parse
import json
import time
import os

WORK_DIR = "/sessions/modest-compassionate-cray"
INPUT_FILE = os.path.join(WORK_DIR, "all_langs_top50.json")
OUTPUT_FILE = os.path.join(WORK_DIR, "all_wikidata.json")
PROGRESS_FILE = os.path.join(WORK_DIR, "wd_progress.json")

def query_wikidata(lang, titles, max_retries=2):
    """Query Wikidata for a batch of titles from a specific wiki."""
    results = {}
    batch_size = 50

    for i in range(0, len(titles), batch_size):
        batch = titles[i:i+batch_size]
        tp = '|'.join([t.replace(' ', '_') for t in batch])

        # Map special language codes to wiki names
        wiki_name = lang + 'wiki'
        # Handle special cases
        special_map = {
            'simple': 'simplewiki',
            'zh-yue': 'zh_yuewiki',
            'zh-min-nan': 'zh_min_nanwiki',
            'zh-classical': 'zh_classicalwiki',
            'be-x-old': 'be_x_oldwiki',
            'bat-smg': 'bat_smgwiki',
            'fiu-vro': 'fiu_vrowiki',
            'nds-nl': 'nds_nlwiki',
            'map-bms': 'map_bmswiki',
            'cbk-zam': 'cbk_zamwiki',
            'roa-rup': 'roa_rupwiki',
            'roa-tara': 'roa_tarawiki',
        }
        if lang in special_map:
            wiki_name = special_map[lang]

        url = (f'https://www.wikidata.org/w/api.php?action=wbgetentities'
               f'&sites={wiki_name}'
               f'&titles={urllib.parse.quote(tp)}'
               f'&props=labels|sitelinks'
               f'&languages=en'
               f'&format=json')

        for attempt in range(max_retries):
            req = urllib.request.Request(url, headers={'User-Agent': 'WikiMedAnalysis/1.0'})
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = json.loads(response.read().decode('utf-8'))

                entities = data.get('entities', {})
                for qid, entity in entities.items():
                    if qid.startswith('-') or 'missing' in entity:
                        continue
                    en_label = entity.get('labels', {}).get('en', {}).get('value', '')
                    sitelink = entity.get('sitelinks', {}).get(wiki_name, {})
                    wiki_title = sitelink.get('title', '')
                    en_sitelink = entity.get('sitelinks', {}).get('enwiki', {})
                    en_wiki_title = en_sitelink.get('title', '')
                    display_name = en_wiki_title or en_label or wiki_title

                    for t in batch:
                        if t.replace(' ', '_') == wiki_title.replace(' ', '_'):
                            results[t] = {'qid': qid, 'en_label': display_name}
                            break
                break  # Success
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)
                # Silently skip on failure

        time.sleep(0.2)

    return results


if __name__ == '__main__':
    print("Loading article data...")
    with open(INPUT_FILE) as f:
        all_data = json.load(f)

    # Load checkpoint
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE) as f:
            wd_results = json.load(f)
        print(f"Resuming from checkpoint: {len(wd_results)} languages done")
    else:
        wd_results = {}

    langs = sorted(all_data.keys())
    total = len(langs)
    done = 0
    skipped = 0

    for lang in langs:
        if lang in wd_results:
            done += 1
            continue

        articles = all_data[lang]
        if not articles:
            wd_results[lang] = {}
            done += 1
            skipped += 1
            continue

        titles = [a['title'] for a in articles]
        results = query_wikidata(lang, titles)
        wd_results[lang] = results
        done += 1

        matched = len(results)
        total_titles = len(titles)

        if done % 50 == 0 or done == total:
            print(f"[{done}/{total}] {lang}: {matched}/{total_titles} matched", flush=True)
            # Checkpoint
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(wd_results, f, ensure_ascii=False)
        elif done % 10 == 0:
            print(f"[{done}/{total}] {lang}: {matched}/{total_titles}", flush=True)

    # Final save
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(wd_results, f, ensure_ascii=False)

    # Stats
    total_matched = sum(len(v) for v in wd_results.values())
    total_titles = sum(len(all_data[l]) for l in all_data)
    print(f"\n{'='*60}")
    print(f"DONE: {total} languages processed")
    print(f"Total titles: {total_titles}, Matched: {total_matched} ({100*total_matched/total_titles:.1f}%)")
    print(f"Saved to {OUTPUT_FILE}")
