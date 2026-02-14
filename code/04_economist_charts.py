#!/usr/bin/env python3
"""
Economist-style visualizations for Wikipedia Medicine cross-language overlap.
One graph per image. Clean typography, signature red accent bar, muted palette.
"""

import json
import os
import numpy as np
from collections import defaultdict, Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe

WORK_DIR = "/sessions/modest-compassionate-cray"
OUTPUT_DIR = "/sessions/modest-compassionate-cray/mnt/outputs"

# ============================================================
# ECONOMIST STYLE THEME
# ============================================================
# Economist palette
ECO_RED = '#E3120B'
ECO_DARK = '#1A1A2E'
ECO_BLUE = '#006BA6'
ECO_LIGHT_BLUE = '#3EBCD2'
ECO_TEAL = '#00847E'
ECO_GREY = '#758D99'
ECO_LIGHT_GREY = '#D9E1E2'
ECO_BG = '#F7F5F0'       # Warm off-white like The Economist
ECO_GRID = '#DAD5CC'
ECO_TEXT = '#333333'
ECO_SUBTITLE = '#666666'

# Qualitative palette (Economist-ish)
ECO_PALETTE = ['#E3120B', '#006BA6', '#00847E', '#3EBCD2', '#9B59B6',
               '#E67E22', '#758D99', '#2ECC71', '#F39C12', '#1ABC9C']


def economist_style(fig, ax, title, subtitle, source='Source: mdwiki.toolforge.org / Wikidata',
                    title_y=0.98, subtitle_y=None, pad_top=0.88):
    """Apply Economist styling to a matplotlib figure."""
    fig.patch.set_facecolor(ECO_BG)
    ax.set_facecolor(ECO_BG)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(ECO_LIGHT_GREY)
    ax.spines['bottom'].set_color(ECO_LIGHT_GREY)

    # Tick styling
    ax.tick_params(colors=ECO_TEXT, labelsize=9)
    ax.tick_params(axis='x', length=0)
    ax.tick_params(axis='y', length=0)

    # Grid
    ax.grid(axis='y', color=ECO_GRID, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)

    # Signature red bar at top
    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0.02, 0.95), 0.12, 0.035,
            boxstyle="square,pad=0",
            facecolor=ECO_RED, edgecolor='none',
            transform=fig.transFigure, zorder=10
        )
    )

    # Title (bold, dark, left-aligned)
    fig.text(0.02, title_y - 0.06, title,
             fontsize=15, fontweight='bold', color=ECO_DARK,
             fontfamily='serif', ha='left', va='top',
             transform=fig.transFigure)

    # Subtitle (lighter, smaller, left-aligned) — extra gap to avoid overlap
    if subtitle_y is None:
        subtitle_y = title_y - 0.06 - 0.055
    fig.text(0.02, subtitle_y, subtitle,
             fontsize=10, color=ECO_SUBTITLE,
             fontfamily='serif', ha='left', va='top',
             transform=fig.transFigure)

    # Source at bottom left
    fig.text(0.02, 0.01, source,
             fontsize=7, color=ECO_GREY,
             fontfamily='serif', ha='left', va='bottom',
             transform=fig.transFigure)

    # Adjust plot area
    plt.subplots_adjust(top=pad_top, bottom=0.08, left=0.15, right=0.95)


def economist_style_heatmap(fig, title, subtitle, source='Source: mdwiki.toolforge.org / Wikidata',
                            title_y=0.98, subtitle_y=None):
    """Economist styling for heatmaps (no axis-level grid changes)."""
    fig.patch.set_facecolor(ECO_BG)

    fig.patches.append(
        mpatches.FancyBboxPatch(
            (0.02, 0.96), 0.08, 0.025,
            boxstyle="square,pad=0",
            facecolor=ECO_RED, edgecolor='none',
            transform=fig.transFigure, zorder=10
        )
    )

    fig.text(0.02, title_y - 0.05, title,
             fontsize=14, fontweight='bold', color=ECO_DARK,
             fontfamily='serif', ha='left', va='top',
             transform=fig.transFigure)

    if subtitle_y is None:
        subtitle_y = title_y - 0.05 - 0.05
    fig.text(0.02, subtitle_y, subtitle,
             fontsize=9.5, color=ECO_SUBTITLE,
             fontfamily='serif', ha='left', va='top',
             transform=fig.transFigure)

    fig.text(0.02, 0.01, source,
             fontsize=7, color=ECO_GREY,
             fontfamily='serif', ha='left', va='bottom',
             transform=fig.transFigure)


# ============================================================
# LOAD DATA
# ============================================================
print("Loading data...")

with open(os.path.join(WORK_DIR, "all_langs_top50.json")) as f:
    all_articles = json.load(f)

with open(os.path.join(WORK_DIR, "all_wikidata.json")) as f:
    all_wikidata = json.load(f)

import urllib.request
url = 'https://mdwiki.toolforge.org/views/api.php?sub_dir=users-agents'
req = urllib.request.Request(url, headers={'User-Agent': 'WikiMedAnalysis/1.0'})
with urllib.request.urlopen(req, timeout=60) as response:
    lang_meta = json.loads(response.read().decode('utf-8'))

lang_info = {}
for item in lang_meta['data']:
    if not item['is_summary']:
        lang_info[item['lang']] = {'titles': item['titles'], 'total': item['total']}

# Build unified map
unified = defaultdict(lambda: {'en_label': '', 'langs': {}})

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

sorted_articles = sorted(
    unified.items(),
    key=lambda x: (-len(x[1]['langs']), -sum(d['total'] for d in x[1]['langs'].values()))
)

overlap_counts = Counter(len(info['langs']) for info in unified.values())
all_n_langs = [len(info['langs']) for info in unified.values()]
total_unique = len(unified)

print(f"Loaded {total_unique} unique articles across {len(all_articles)} languages")


# ============================================================
# FIGURE 1: Top 30 most universal articles
# ============================================================
print("\nFig 1: Top 30 most universal articles...")

top30 = sorted_articles[:30]
labels = [info['en_label'][:38] for _, info in top30]
n_langs = [len(info['langs']) for _, info in top30]

fig, ax = plt.subplots(figsize=(8, 10))

# Color: top article gets red, rest get blue gradient
colors = [ECO_RED if i == 0 else ECO_BLUE for i in range(len(labels))]
# Make alternating slightly lighter for readability
colors = [ECO_RED if i == 0 else (ECO_BLUE if i % 2 == 0 else '#2980B9') for i in range(len(labels))]

bars = ax.barh(range(len(labels)), n_langs, color=colors, height=0.72, edgecolor='none')

# Value labels
for i, (bar, n) in enumerate(zip(bars, n_langs)):
    ax.text(bar.get_width() + 1.5, i, str(n),
            va='center', fontsize=8, color=ECO_TEXT, fontfamily='serif')

ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=8, fontfamily='serif', color=ECO_TEXT)
ax.invert_yaxis()
ax.set_xlabel('')
ax.set_xlim(0, max(n_langs) + 15)

# Remove y-axis spine for cleaner look
ax.spines['left'].set_visible(False)

economist_style(fig, ax,
    title='The world reads about hearts',
    subtitle='Number of Wikipedia language editions where each medical\narticle ranks in the top 50 most viewed, out of 337 total',
    title_y=0.99, subtitle_y=0.885, pad_top=0.84)

plt.subplots_adjust(left=0.30, right=0.92, top=0.84, bottom=0.05)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig1_universal_articles.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig1")


# ============================================================
# FIGURE 2: Overlap distribution histogram
# ============================================================
print("Fig 2: Overlap distribution...")

fig, ax = plt.subplots(figsize=(8, 5.5))

# Bin the data: 1, 2-5, 6-10, 11-20, 21-50, 51-100, 100+
bins_custom = [1, 2, 6, 11, 21, 51, 101, 200]
bin_labels = ['1', '2–5', '6–10', '11–20', '21–50', '51–100', '100+']
counts_binned = []
for i in range(len(bins_custom)-1):
    lo = bins_custom[i]
    hi = bins_custom[i+1]
    c = sum(1 for n in all_n_langs if lo <= n < hi)
    counts_binned.append(c)

bar_colors = [ECO_GREY] + [ECO_BLUE]*5 + [ECO_RED]
bars = ax.bar(range(len(bin_labels)), counts_binned, color=bar_colors,
              edgecolor='none', width=0.7)

for bar, val in zip(bars, counts_binned):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 15,
            f'{val:,}', ha='center', fontsize=9, color=ECO_TEXT, fontfamily='serif')

ax.set_xticks(range(len(bin_labels)))
ax.set_xticklabels(bin_labels, fontsize=9, fontfamily='serif')
ax.set_ylabel('')

economist_style(fig, ax,
    title='Most articles stay local',
    subtitle='Number of unique medical articles by how many language\neditions include them in their top 50 most viewed',
    title_y=0.99, subtitle_y=0.875, pad_top=0.82)

# Add annotation
single = overlap_counts.get(1, 0)
multi = sum(v for k, v in overlap_counts.items() if k > 1)
ax.text(0.97, 0.92, f'{single:,} articles appear in\nonly one language\'s top 50\n\n{multi:,} appear in two\nor more languages',
        transform=ax.transAxes, ha='right', va='top', fontsize=8.5,
        color=ECO_SUBTITLE, fontfamily='serif',
        bbox=dict(boxstyle='square,pad=0.4', facecolor=ECO_BG, edgecolor=ECO_LIGHT_GREY, linewidth=0.5))

plt.subplots_adjust(left=0.10, right=0.95, top=0.82, bottom=0.10)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig2_overlap_distribution.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig2")


# ============================================================
# FIGURE 3: Cumulative - articles in N+ languages
# ============================================================
print("Fig 3: Cumulative overlap curve...")

fig, ax = plt.subplots(figsize=(8, 5.5))

thresholds = list(range(1, max(all_n_langs)+1))
cumulative = [sum(1 for n in all_n_langs if n >= t) for t in thresholds]

ax.fill_between(thresholds, cumulative, alpha=0.15, color=ECO_BLUE)
ax.plot(thresholds, cumulative, color=ECO_BLUE, linewidth=2.5)

# Key annotations
annotations = [(2, 'articles in 2+'), (10, 'in 10+'), (50, 'in 50+'), (100, 'in 100+')]
for thresh, label in annotations:
    count = sum(1 for n in all_n_langs if n >= thresh)
    if count > 0:
        ax.plot(thresh, count, 'o', color=ECO_RED, markersize=5, zorder=5)
        ax.annotate(f'{count} {label}', xy=(thresh, count),
                    xytext=(8, 8), textcoords='offset points',
                    fontsize=8, fontfamily='serif', color=ECO_RED,
                    arrowprops=dict(arrowstyle='-', color=ECO_RED, lw=0.5))

ax.set_yscale('log')
ax.set_xlabel('Minimum number of languages', fontsize=9, fontfamily='serif', color=ECO_TEXT)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{int(x):,}' if x >= 1 else ''))

economist_style(fig, ax,
    title='A steep drop-off in universality',
    subtitle='Number of medical articles appearing in at least N languages\' top 50.\nThe curve falls sharply: very few topics are globally universal.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.80)

plt.subplots_adjust(left=0.12, right=0.95, top=0.80, bottom=0.12)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig3_cumulative.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig3")


# ============================================================
# FIGURE 4: Article × Language heatmap (top 20 × 20)
# ============================================================
print("Fig 4: Article-Language heatmap...")

top20_langs = sorted(lang_info.keys(), key=lambda l: lang_info[l]['total'], reverse=True)[:20]
top20_articles = sorted_articles[:20]

LANG_NAMES = {
    'en': 'EN', 'es': 'ES', 'de': 'DE', 'ru': 'RU',
    'fr': 'FR', 'ja': 'JA', 'it': 'IT', 'pt': 'PT',
    'fa': 'FA', 'pl': 'PL', 'zh': 'ZH', 'ar': 'AR',
    'nl': 'NL', 'sv': 'SV', 'uk': 'UK', 'cs': 'CS',
    'tr': 'TR', 'he': 'HE', 'id': 'ID', 'fi': 'FI'
}

art_labels = [info['en_label'][:30] for _, info in top20_articles]
lang_labels = [LANG_NAMES.get(l, l) for l in top20_langs]

rank_matrix = np.full((len(top20_articles), len(top20_langs)), np.nan)
for i, (qid, info) in enumerate(top20_articles):
    for j, lang in enumerate(top20_langs):
        if lang in info['langs']:
            rank_matrix[i, j] = info['langs'][lang]['rank']

# Custom Economist-style colormap: warm tones
eco_cmap = LinearSegmentedColormap.from_list('eco',
    ['#E3120B', '#E67E22', '#F5D76E', '#F7F5F0'], N=256)

fig, ax = plt.subplots(figsize=(9, 9))

# Plot heatmap manually for more control
masked = np.ma.masked_invalid(rank_matrix)
im = ax.imshow(masked, cmap=eco_cmap, aspect='auto', vmin=1, vmax=50,
               interpolation='nearest')

# Add rank text in cells
for i in range(len(top20_articles)):
    for j in range(len(top20_langs)):
        if not np.isnan(rank_matrix[i, j]):
            val = int(rank_matrix[i, j])
            text_color = 'white' if val <= 10 else ECO_DARK
            ax.text(j, i, str(val), ha='center', va='center',
                    fontsize=7, fontfamily='serif', color=text_color, fontweight='bold')
        else:
            ax.add_patch(plt.Rectangle((j-0.5, i-0.5), 1, 1,
                        facecolor='#E8E4DE', edgecolor='white', linewidth=0.5))

ax.set_xticks(range(len(lang_labels)))
ax.set_xticklabels(lang_labels, fontsize=8, fontfamily='serif', color=ECO_TEXT, rotation=0)
ax.set_yticks(range(len(art_labels)))
ax.set_yticklabels(art_labels, fontsize=8, fontfamily='serif', color=ECO_TEXT)

# Grid lines
for i in range(len(top20_articles)+1):
    ax.axhline(i-0.5, color='white', linewidth=0.5)
for j in range(len(top20_langs)+1):
    ax.axvline(j-0.5, color='white', linewidth=0.5)

ax.tick_params(length=0)

# Colorbar
cbar = fig.colorbar(im, ax=ax, shrink=0.4, pad=0.02, aspect=20)
cbar.set_label('Rank in top 50', fontsize=8, fontfamily='serif', color=ECO_TEXT)
cbar.ax.tick_params(labelsize=7)
cbar.ax.invert_yaxis()

economist_style_heatmap(fig,
    title='What the world reads about medicine',
    subtitle='Rank of each article in each language\'s top 50 most-viewed medical pages.\nDarker red = higher rank. Grey = not in that language\'s top 50.',
    title_y=0.995, subtitle_y=0.91)

plt.subplots_adjust(left=0.22, right=0.88, top=0.86, bottom=0.04)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig4_heatmap.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig4")


# ============================================================
# FIGURE 5: Language pair overlap (top 20)
# ============================================================
print("Fig 5: Language pair overlap matrix...")

n_l = len(top20_langs)
pair_matrix = np.zeros((n_l, n_l), dtype=int)

multi = [(qid, info) for qid, info in unified.items() if len(info['langs']) > 1]
for qid, info in multi:
    art_langs = set(info['langs'].keys())
    for i, l1 in enumerate(top20_langs):
        for j, l2 in enumerate(top20_langs):
            if l1 in art_langs and l2 in art_langs:
                pair_matrix[i, j] += 1

# Use lower triangle only (cleaner)
eco_blue_cmap = LinearSegmentedColormap.from_list('eco_blue',
    ['#F7F5F0', '#B8D4E3', '#006BA6', '#003F5C'], N=256)

fig, ax = plt.subplots(figsize=(9, 9))

im = ax.imshow(pair_matrix, cmap=eco_blue_cmap, aspect='equal', vmin=0,
               interpolation='nearest')

LANG_FULL = {
    'en': 'English', 'es': 'Spanish', 'de': 'German', 'ru': 'Russian',
    'fr': 'French', 'ja': 'Japanese', 'it': 'Italian', 'pt': 'Portuguese',
    'fa': 'Persian', 'pl': 'Polish', 'zh': 'Chinese', 'ar': 'Arabic',
    'nl': 'Dutch', 'sv': 'Swedish', 'uk': 'Ukrainian', 'cs': 'Czech',
    'tr': 'Turkish', 'he': 'Hebrew', 'id': 'Indonesian', 'fi': 'Finnish'
}

full_labels = [LANG_FULL.get(l, l) for l in top20_langs]

for i in range(n_l):
    for j in range(n_l):
        val = pair_matrix[i, j]
        text_color = 'white' if val > 30 else ECO_DARK
        ax.text(j, i, str(val), ha='center', va='center',
                fontsize=6.5, fontfamily='serif', color=text_color)

ax.set_xticks(range(n_l))
ax.set_xticklabels(full_labels, fontsize=7.5, fontfamily='serif', color=ECO_TEXT, rotation=45, ha='right')
ax.set_yticks(range(n_l))
ax.set_yticklabels(full_labels, fontsize=7.5, fontfamily='serif', color=ECO_TEXT)

for i in range(n_l+1):
    ax.axhline(i-0.5, color='white', linewidth=0.5)
    ax.axvline(i-0.5, color='white', linewidth=0.5)
ax.tick_params(length=0)

cbar = fig.colorbar(im, ax=ax, shrink=0.4, pad=0.02, aspect=20)
cbar.set_label('Shared articles in top 50', fontsize=8, fontfamily='serif', color=ECO_TEXT)
cbar.ax.tick_params(labelsize=7)

economist_style_heatmap(fig,
    title='European languages cluster together',
    subtitle='Number of medical articles that two languages share in their respective\ntop-50 most-viewed lists. Top 20 Wikipedia language editions shown.',
    title_y=0.995, subtitle_y=0.91)

plt.subplots_adjust(left=0.13, right=0.88, top=0.87, bottom=0.12)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig5_language_pairs.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig5")


# ============================================================
# FIGURE 6: Thematic categories - article count
# ============================================================
print("Fig 6: Thematic category breakdown...")

categories = {
    'Mental Health': ['Asperger syndrome', 'Schizophrenia', 'Bipolar disorder',
                      'Autism', 'Borderline personality disorder', 'Depression (mood)',
                      'Attention deficit hyperactivity disorder', 'Obsessive–compulsive disorder',
                      'Tourette syndrome', 'Down syndrome', 'Psychopathy',
                      'Narcissistic personality disorder', 'Anxiety disorder',
                      'Post-traumatic stress disorder', 'Antisocial personality disorder',
                      'Sleep paralysis', 'Dissociative identity disorder', 'Phobia',
                      'Anorexia nervosa'],
    'Infectious diseases': ['Tuberculosis', 'Syphilis', 'HIV/AIDS', 'Malaria',
                          'Smallpox', 'Plague (disease)', 'Lyme disease', 'Monkeypox',
                          'Rabies', 'Leprosy', 'Measles', 'Chickenpox',
                          'Scarlet fever', 'Tetanus', 'Cholera', 'Typhus',
                          'Meningitis', 'Hepatitis B', 'Dengue fever', 'Ebola virus disease'],
    'Pandemics & COVID': ['COVID-19 pandemic', 'COVID-19', 'Spanish flu', 'Black Death',
                          'Coronavirus', 'Pandemic', 'SARS-CoV-2'],
    'Drugs & substances': ['Cocaine', 'Cannabis (drug)', 'MDMA', 'Methamphetamine',
                          'Fentanyl', 'Alprazolam', 'Paracetamol', 'Ethanol',
                          'Clonazepam', 'Ibuprofen', 'LSD', 'Heroin', 'Morphine',
                          'Aspirin', 'Diazepam', 'Tramadol', 'Amphetamine',
                          'Lorazepam', 'Diclofenac', 'Quetiapine', 'Metformin'],
    'Sexuality & reproduction': ['Sexual intercourse', 'Orgasm', 'Circumcision',
                                'Pregnancy', 'Contraception', 'Abortion',
                                'Erectile dysfunction', 'Menstrual cycle',
                                'Human papillomavirus infection', 'Masturbation',
                                'Suicide methods'],
    'Chronic & neurological': ['Multiple sclerosis', "Parkinson's disease", 'Fibromyalgia',
                              'Amyotrophic lateral sclerosis', "Crohn's disease",
                              "Alzheimer's disease", 'Epilepsy', 'Diabetes',
                              'Cancer', 'Lupus', 'Celiac disease', 'Stroke',
                              'Myocardial infarction', 'Hypertension', 'Psoriasis',
                              'Endometriosis', 'Arthritis'],
    'Notable figures': ['Sigmund Freud', 'Marie Curie', 'Josef Mengele', 'Avicenna',
                       'Hippocrates', 'Tasuku Honjo', 'Nostradamus', 'Alexander Fleming',
                       'Joseph Lister', 'Louis Pasteur', 'Florence Nightingale',
                       'Carl Jung', 'Albert Schweitzer'],
    'General medical': ['Virus', 'Blood type', 'Body mass index', 'Heart', 'Blood',
                       "Maslow's hierarchy of needs", 'Lobotomy', 'Gaslighting',
                       'Pneumonia', 'Anesthesia', 'Medicine', 'Antibiotics',
                       'Vaccination', 'World Health Organization', 'Red Cross',
                       'Bacteria', 'DNA', 'Psychological resilience', 'Health',
                       'Death', 'Anatomy', 'Disease', 'Calcium', 'Muscle',
                       'Influenza', 'Suicide']
}

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

# Sort by count (exclude Other)
cats_sorted = sorted([(c, v) for c, v in cat_counts.items() if c != 'Other'],
                     key=lambda x: x[1], reverse=True)

fig, ax = plt.subplots(figsize=(8, 5.5))

cat_names = [c for c, _ in cats_sorted]
cat_vals = [v for _, v in cats_sorted]

# Economist colors for categories
cat_colors = [ECO_RED, ECO_BLUE, ECO_TEAL, ECO_LIGHT_BLUE, '#9B59B6', '#E67E22', ECO_GREY, '#2ECC71']

bars = ax.barh(range(len(cat_names)), cat_vals,
               color=cat_colors[:len(cat_names)], height=0.65, edgecolor='none')

for bar, val in zip(bars, cat_vals):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            str(val), va='center', fontsize=9, color=ECO_TEXT, fontfamily='serif')

ax.set_yticks(range(len(cat_names)))
ax.set_yticklabels(cat_names, fontsize=9.5, fontfamily='serif', color=ECO_TEXT)
ax.invert_yaxis()
ax.spines['left'].set_visible(False)

economist_style(fig, ax,
    title='Infectious diseases and mental health lead',
    subtitle='Number of medical articles appearing in two or more languages\'\ntop 50, grouped by thematic category (excluding uncategorised)',
    title_y=0.99, subtitle_y=0.875, pad_top=0.82)

plt.subplots_adjust(left=0.32, right=0.92, top=0.82, bottom=0.08)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig6_categories.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig6")


# ============================================================
# FIGURE 7: Average language spread by category
# ============================================================
print("Fig 7: Average language spread per category...")

fig, ax = plt.subplots(figsize=(8, 5.5))

avg_langs = {cat: cat_total_langs[cat]/cat_counts[cat] for cat in cat_names if cat_counts[cat] > 0}
cats_by_avg = sorted(avg_langs.items(), key=lambda x: x[1], reverse=True)
avg_names = [c for c, _ in cats_by_avg]
avg_vals = [v for _, v in cats_by_avg]

# Color mapping
color_map = dict(zip(cat_names, cat_colors[:len(cat_names)]))
avg_colors = [color_map.get(c, ECO_GREY) for c in avg_names]

bars = ax.barh(range(len(avg_names)), avg_vals,
               color=avg_colors, height=0.65, edgecolor='none')

for bar, val in zip(bars, avg_vals):
    ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
            f'{val:.1f}', va='center', fontsize=9, color=ECO_TEXT, fontfamily='serif')

ax.set_yticks(range(len(avg_names)))
ax.set_yticklabels(avg_names, fontsize=9.5, fontfamily='serif', color=ECO_TEXT)
ax.invert_yaxis()
ax.spines['left'].set_visible(False)
ax.set_xlim(0, max(avg_vals) + 10)

economist_style(fig, ax,
    title='Pandemics cross every language barrier',
    subtitle='Average number of Wikipedia language editions per overlapping article,\nby thematic category. Pandemics spread across 75 languages on average.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.82)

plt.subplots_adjust(left=0.32, right=0.92, top=0.82, bottom=0.08)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig7_category_spread.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig7")


print(f"\n{'='*60}")
print("ALL 7 ECONOMIST-STYLE CHARTS GENERATED")
print(f"{'='*60}")
