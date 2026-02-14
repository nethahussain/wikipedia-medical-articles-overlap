#!/usr/bin/env python3
"""
Stage 3: Analyze overlap across ALL 337 languages and generate compact visualizations.
"""
import json
import os
import csv
from collections import defaultdict, Counter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import seaborn as sns

WORK_DIR = "/sessions/modest-compassionate-cray"
OUTPUT_DIR = "/sessions/modest-compassionate-cray/mnt/outputs"

# Load data
print("Loading data...")
with open(os.path.join(WORK_DIR, "all_langs_top50.json")) as f:
    all_articles = json.load(f)

with open(os.path.join(WORK_DIR, "all_wikidata.json")) as f:
    all_wikidata = json.load(f)

# Get language info for labels
import urllib.request
url = 'https://mdwiki.toolforge.org/views/api.php?sub_dir=users-agents'
req = urllib.request.Request(url, headers={'User-Agent': 'WikiMedAnalysis/1.0'})
with urllib.request.urlopen(req, timeout=60) as response:
    lang_meta = json.loads(response.read().decode('utf-8'))

lang_info = {}
for item in lang_meta['data']:
    if not item['is_summary']:
        lang_info[item['lang']] = {'titles': item['titles'], 'total': item['total']}

# ============================================================
# Build unified article map across ALL languages
# ============================================================
print("Building unified article map...")

# unified: QID -> {en_label, langs: {lang: {title, total, rank}}}
unified = defaultdict(lambda: {'en_label': '', 'langs': {}})
unmatched_count = 0

for lang in all_articles:
    articles = all_articles[lang]
    wd = all_wikidata.get(lang, {})

    for rank, article in enumerate(articles, 1):
        title = article['title']
        wd_info = wd.get(title)

        if wd_info:
            qid = wd_info['qid']
            if wd_info['en_label']:
                unified[qid]['en_label'] = wd_info['en_label']
            unified[qid]['langs'][lang] = {
                'title': title,
                'total': article['total'],
                'rank': rank
            }
        else:
            unmatched_count += 1

total_unique = len(unified)
overlap_counts = Counter(len(info['langs']) for info in unified.values())

print(f"\nTotal unique articles (Wikidata entities): {total_unique}")
print(f"Unmatched titles: {unmatched_count}")
print(f"\nOverlap distribution:")
for k in sorted(overlap_counts.keys(), reverse=True)[:20]:
    print(f"  In {k:>3d} languages: {overlap_counts[k]:>4d} articles")

# Sort articles by number of languages appearing
sorted_articles = sorted(
    unified.items(),
    key=lambda x: (-len(x[1]['langs']), -sum(d['total'] for d in x[1]['langs'].values()))
)

# Print top overlapping articles
print(f"\n{'='*80}")
print("TOP 30 MOST UNIVERSAL ARTICLES (appearing in most languages' top 50)")
print(f"{'='*80}")
for qid, info in sorted_articles[:30]:
    n = len(info['langs'])
    total_views = sum(d['total'] for d in info['langs'].values())
    print(f"\n  {info['en_label'][:60]} ({qid})")
    print(f"    Appears in {n} languages | Total views: {total_views:,}")
    # Show top 5 languages by views
    top_l = sorted(info['langs'].items(), key=lambda x: x[1]['total'], reverse=True)[:5]
    for lang, d in top_l:
        print(f"      {lang}: #{d['rank']} ({d['total']:,} views)")
    if n > 5:
        print(f"      ... and {n-5} more languages")


# ============================================================
# SAVE CSV WITH FULL DATA
# ============================================================
print(f"\nSaving comprehensive CSV...")
csv_path = os.path.join(OUTPUT_DIR, 'all_languages_overlap_analysis.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(['Wikidata_QID', 'English_Label', 'Num_Languages', 'Total_Views_All_Langs',
                     'Languages', 'Top5_Languages_Detail'])
    for qid, info in sorted_articles:
        n = len(info['langs'])
        total_views = sum(d['total'] for d in info['langs'].values())
        lang_list = ', '.join(sorted(info['langs'].keys()))
        top5 = sorted(info['langs'].items(), key=lambda x: x[1]['total'], reverse=True)[:5]
        top5_str = '; '.join([f"{l}:#{d['rank']}({d['total']:,})" for l, d in top5])
        writer.writerow([qid, info['en_label'], n, total_views, lang_list, top5_str])

print(f"  Saved {csv_path}")

# ============================================================
# SAVE JSON SUMMARY
# ============================================================
summary = {
    'total_languages': len(all_articles),
    'total_unique_articles_wikidata': total_unique,
    'overlap_distribution': {str(k): v for k, v in sorted(overlap_counts.items(), reverse=True)},
    'top_100_overlapping': []
}

for qid, info in sorted_articles[:100]:
    summary['top_100_overlapping'].append({
        'qid': qid,
        'en_label': info['en_label'],
        'num_languages': len(info['langs']),
        'total_views': sum(d['total'] for d in info['langs'].values()),
        'languages': {l: {'rank': d['rank'], 'views': d['total'], 'title': d['title']}
                     for l, d in info['langs'].items()}
    })

summary_path = os.path.join(OUTPUT_DIR, 'all_languages_summary.json')
with open(summary_path, 'w') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
print(f"  Saved {summary_path}")


# ============================================================
# FIGURE 1: Top 30 most universal articles - horizontal bar
# ============================================================
print("\nGenerating Figure 1: Most Universal Articles...")

top30 = sorted_articles[:30]
labels = [info['en_label'][:40] for _, info in top30]
n_langs = [len(info['langs']) for _, info in top30]
total_views = [sum(d['total'] for d in info['langs'].values()) for _, info in top30]

fig, ax = plt.subplots(figsize=(10, 9))

norm = plt.Normalize(min(total_views), max(total_views))
colors = plt.cm.YlOrRd(norm(total_views))

bars = ax.barh(range(len(labels)), n_langs, color=colors, edgecolor='white', height=0.75)

for i, (bar, n, tv) in enumerate(zip(bars, n_langs, total_views)):
    ax.text(bar.get_width() + 0.5, i, f'{n} langs | {tv/1e6:.0f}M views',
            va='center', fontsize=6.5, color='#333')

ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=7.5)
ax.invert_yaxis()
ax.set_xlabel('Number of Languages in Top 50', fontsize=10)
ax.set_title('Top 30 Most Universal Medical Articles\nAcross All 337 Wikipedia Language Editions',
             fontsize=12, fontweight='bold')
ax.set_xlim(0, max(n_langs) + 25)
ax.grid(axis='x', alpha=0.2)
ax.axvline(x=337*0.5, color='gray', linestyle=':', alpha=0.3)

sm = plt.cm.ScalarMappable(cmap='YlOrRd', norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.4, pad=0.01)
cbar.set_label('Total Views', fontsize=8)
cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M'))

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'fig1_all_most_universal_articles.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  Saved fig1")


# ============================================================
# FIGURE 2: Overlap distribution (histogram)
# ============================================================
print("Generating Figure 2: Overlap Distribution...")

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Left: Full distribution
all_n_langs = [len(info['langs']) for info in unified.values()]
bins = range(1, max(all_n_langs)+2)

ax1.hist(all_n_langs, bins=bins, color='#4f46e5', edgecolor='white', alpha=0.85, align='left')
ax1.set_xlabel('Number of Languages', fontsize=10)
ax1.set_ylabel('Number of Articles', fontsize=10)
ax1.set_title('How Many Languages Share\nthe Same Top-50 Article?', fontsize=11, fontweight='bold')
ax1.set_yscale('log')
ax1.grid(axis='y', alpha=0.2)

# Add annotation
single = overlap_counts.get(1, 0)
multi = sum(v for k, v in overlap_counts.items() if k > 1)
ax1.text(0.95, 0.95, f'1 language only: {single}\n2+ languages: {multi}\nTotal unique: {total_unique}',
         transform=ax1.transAxes, ha='right', va='top', fontsize=8,
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Right: Cumulative - what % of articles appear in N+ languages
thresholds = list(range(1, max(all_n_langs)+1))
cumulative = [sum(1 for n in all_n_langs if n >= t) for t in thresholds]
ax2.plot(thresholds, cumulative, color='#dc2626', linewidth=2, marker='o', markersize=3)
ax2.fill_between(thresholds, cumulative, alpha=0.1, color='#dc2626')
ax2.set_xlabel('Appearing in N+ Languages', fontsize=10)
ax2.set_ylabel('Number of Articles', fontsize=10)
ax2.set_title('Cumulative: Articles Appearing\nin N or More Languages', fontsize=11, fontweight='bold')
ax2.set_yscale('log')
ax2.grid(alpha=0.2)

# Annotate key points
for threshold in [5, 10, 20, 50, 100]:
    count = sum(1 for n in all_n_langs if n >= threshold)
    if count > 0:
        ax2.annotate(f'{count} articles', xy=(threshold, count),
                    fontsize=7, ha='left', va='bottom',
                    xytext=(5, 5), textcoords='offset points')

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'fig2_all_overlap_distribution.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  Saved fig2")


# ============================================================
# FIGURE 3: Heatmap - top 20 articles × top 20 languages
# ============================================================
print("Generating Figure 3: Article-Language Heatmap (top 20×20)...")

# Top 20 languages by total views
top20_langs = sorted(lang_info.keys(), key=lambda l: lang_info[l]['total'], reverse=True)[:20]

# Top 20 articles appearing in the most languages (with a preference for high views)
top20_articles = sorted_articles[:20]

LANG_NAMES = {
    'en': 'English', 'es': 'Spanish', 'de': 'German', 'ru': 'Russian',
    'fr': 'French', 'ja': 'Japanese', 'it': 'Italian', 'pt': 'Portuguese',
    'fa': 'Persian', 'pl': 'Polish', 'zh': 'Chinese', 'ar': 'Arabic',
    'nl': 'Dutch', 'sv': 'Swedish', 'uk': 'Ukrainian', 'cs': 'Czech',
    'tr': 'Turkish', 'he': 'Hebrew', 'id': 'Indonesian', 'fi': 'Finnish'
}

art_labels = [info['en_label'][:35] for _, info in top20_articles]
lang_labels = [LANG_NAMES.get(l, l) for l in top20_langs]

# Build rank matrix
rank_matrix = np.zeros((len(top20_articles), len(top20_langs)))
views_matrix = np.zeros((len(top20_articles), len(top20_langs)))

for i, (qid, info) in enumerate(top20_articles):
    for j, lang in enumerate(top20_langs):
        if lang in info['langs']:
            rank_matrix[i, j] = info['langs'][lang]['rank']
            views_matrix[i, j] = np.log10(max(info['langs'][lang]['total'], 1))

fig, ax = plt.subplots(figsize=(12, 9))
cmap = plt.cm.YlOrRd.copy()
cmap.set_under('#f8f8f8')
mask = views_matrix == 0

sns.heatmap(
    views_matrix, mask=mask,
    xticklabels=lang_labels, yticklabels=art_labels,
    cmap=cmap, vmin=4.5, vmax=8,
    annot=rank_matrix.astype(int), fmt='d',
    linewidths=0.5, linecolor='#e0e0e0',
    cbar_kws={'label': 'log₁₀(Views)', 'shrink': 0.5},
    ax=ax, square=False
)

for text in ax.texts:
    if text.get_text() == '0':
        text.set_text('')
    else:
        text.set_fontsize(7)
        text.set_fontweight('bold')

# Gray background for missing
for i in range(len(top20_articles)):
    for j in range(len(top20_langs)):
        if mask[i, j]:
            ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=True, color='#f0f0f0', ec='#e0e0e0', lw=0.5))

ax.set_title('Top 20 Universal Medical Articles × Top 20 Languages\n(Numbers = rank in that language\'s top 50)',
             fontsize=11, fontweight='bold', pad=10)
ax.tick_params(axis='y', labelsize=8)
ax.tick_params(axis='x', labelsize=8, rotation=35)

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'fig3_all_heatmap_20x20.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  Saved fig3")


# ============================================================
# FIGURE 4: Language-pair overlap for top 20 languages
# ============================================================
print("Generating Figure 4: Language Pair Overlap (top 20)...")

n = len(top20_langs)
pair_matrix = np.zeros((n, n), dtype=int)

# Get all articles appearing in 2+ languages
multi = [(qid, info) for qid, info in unified.items() if len(info['langs']) > 1]

for qid, info in multi:
    art_langs = set(info['langs'].keys())
    for i, l1 in enumerate(top20_langs):
        for j, l2 in enumerate(top20_langs):
            if l1 in art_langs and l2 in art_langs:
                pair_matrix[i, j] += 1

fig, ax = plt.subplots(figsize=(10, 9))

sns.heatmap(
    pair_matrix,
    xticklabels=lang_labels, yticklabels=lang_labels,
    cmap='Blues', annot=True, fmt='d',
    linewidths=0.5, linecolor='white',
    cbar_kws={'label': 'Shared Top-50 Articles', 'shrink': 0.6},
    ax=ax, square=True, vmin=0
)

ax.set_title('Language Pair Overlap in Top 50 Medical Articles\n(Top 20 Wikipedia Languages)',
             fontsize=11, fontweight='bold', pad=10)
ax.tick_params(axis='both', labelsize=8)

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'fig4_all_language_pair_20x20.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  Saved fig4")


# ============================================================
# FIGURE 5: Category analysis - what types of articles overlap most
# ============================================================
print("Generating Figure 5: Thematic Categories of Overlapping Articles...")

# Manually categorize the top overlapping articles by medical theme
# Based on the article titles
categories = {
    'Mental Health': ['Asperger syndrome', 'Schizophrenia', 'Bipolar disorder',
                      'Autism', 'Borderline personality disorder', 'Depression (mood)',
                      'Attention deficit hyperactivity disorder', 'Obsessive–compulsive disorder',
                      'Tourette syndrome', 'Down syndrome', 'Psychopathy',
                      'Narcissistic personality disorder', 'Anxiety disorder',
                      'Post-traumatic stress disorder', 'Antisocial personality disorder',
                      'Sleep paralysis', 'Dissociative identity disorder', 'Phobia',
                      'Anorexia nervosa'],
    'Infectious Disease': ['Tuberculosis', 'Syphilis', 'HIV/AIDS', 'Malaria',
                          'Smallpox', 'Plague (disease)', 'Lyme disease', 'Monkeypox',
                          'Rabies', 'Leprosy', 'Measles', 'Chickenpox',
                          'Scarlet fever', 'Tetanus', 'Cholera', 'Typhus',
                          'Meningitis', 'Hepatitis B', 'Dengue fever', 'Ebola virus disease'],
    'Pandemics & COVID': ['COVID-19 pandemic', 'COVID-19', 'Spanish flu', 'Black Death',
                          'Coronavirus', 'Pandemic', 'SARS-CoV-2'],
    'Drugs & Substances': ['Cocaine', 'Cannabis (drug)', 'MDMA', 'Methamphetamine',
                          'Fentanyl', 'Alprazolam', 'Paracetamol', 'Ethanol',
                          'Clonazepam', 'Ibuprofen', 'LSD', 'Heroin', 'Morphine',
                          'Aspirin', 'Diazepam', 'Tramadol', 'Amphetamine',
                          'Lorazepam', 'Diclofenac', 'Quetiapine', 'Metformin'],
    'Sexuality & Reproduction': ['Sexual intercourse', 'Orgasm', 'Circumcision',
                                'Pregnancy', 'Contraception', 'Abortion',
                                'Erectile dysfunction', 'Menstrual cycle',
                                'Human papillomavirus infection', 'Masturbation',
                                'Suicide methods'],
    'Chronic & Neurological': ['Multiple sclerosis', "Parkinson's disease", 'Fibromyalgia',
                              'Amyotrophic lateral sclerosis', "Crohn's disease",
                              "Alzheimer's disease", 'Epilepsy', 'Diabetes',
                              'Cancer', 'Lupus', 'Celiac disease', 'Stroke',
                              'Myocardial infarction', 'Hypertension', 'Psoriasis',
                              'Endometriosis', 'Arthritis'],
    'Notable Figures': ['Sigmund Freud', 'Marie Curie', 'Josef Mengele', 'Avicenna',
                       'Hippocrates', 'Tasuku Honjo', 'Nostradamus', 'Alexander Fleming',
                       'Joseph Lister', 'Louis Pasteur', 'Florence Nightingale',
                       'Carl Jung', 'Albert Schweitzer'],
    'General Medical': ['Virus', 'Blood type', 'Body mass index', 'Heart',
                       "Maslow's hierarchy of needs", 'Lobotomy', 'Gaslighting',
                       'Pneumonia', 'Anesthesia', 'Medicine', 'Antibiotics',
                       'Vaccination', 'World Health Organization', 'Red Cross',
                       'Bacteria', 'DNA', 'Psychological resilience']
}

# Classify overlapping articles
cat_counts = Counter()
cat_total_langs = defaultdict(int)

for qid, info in sorted_articles:
    if len(info['langs']) < 2:
        continue
    label = info['en_label']
    classified = False
    for cat, keywords in categories.items():
        if label in keywords:
            cat_counts[cat] += 1
            cat_total_langs[cat] += len(info['langs'])
            classified = True
            break
    if not classified:
        cat_counts['Other'] += 1
        cat_total_langs['Other'] += len(info['langs'])

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Left: Number of overlapping articles per category
cats_sorted = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
cat_names = [c for c, _ in cats_sorted]
cat_vals = [v for _, v in cats_sorted]

colors_cat = plt.cm.Set2(np.linspace(0, 1, len(cat_names)))
bars = ax1.barh(range(len(cat_names)), cat_vals, color=colors_cat, edgecolor='white')
ax1.set_yticks(range(len(cat_names)))
ax1.set_yticklabels(cat_names, fontsize=9)
ax1.invert_yaxis()
ax1.set_xlabel('Number of Articles in 2+ Languages', fontsize=9)
ax1.set_title('Overlapping Articles by Category', fontsize=11, fontweight='bold')
for bar, val in zip(bars, cat_vals):
    ax1.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, str(val),
             va='center', fontsize=8)
ax1.grid(axis='x', alpha=0.2)

# Right: Average number of languages per category
avg_langs = {cat: cat_total_langs[cat]/cat_counts[cat] for cat in cat_names if cat_counts[cat] > 0}
avg_sorted = [(cat, avg_langs.get(cat, 0)) for cat in cat_names]
avg_vals = [v for _, v in avg_sorted]

bars2 = ax2.barh(range(len(cat_names)), avg_vals, color=colors_cat, edgecolor='white')
ax2.set_yticks(range(len(cat_names)))
ax2.set_yticklabels(cat_names, fontsize=9)
ax2.invert_yaxis()
ax2.set_xlabel('Average Number of Languages', fontsize=9)
ax2.set_title('Avg. Language Spread per Category', fontsize=11, fontweight='bold')
for bar, val in zip(bars2, avg_vals):
    ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, f'{val:.1f}',
             va='center', fontsize=8)
ax2.grid(axis='x', alpha=0.2)

plt.tight_layout()
fig.savefig(os.path.join(OUTPUT_DIR, 'fig5_all_category_analysis.png'), dpi=130, bbox_inches='tight')
plt.close()
print("  Saved fig5")


print(f"\n{'='*70}")
print("ALL ANALYSIS COMPLETE!")
print(f"{'='*70}")
print(f"Output files in: {OUTPUT_DIR}/")
