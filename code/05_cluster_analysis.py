#!/usr/bin/env python3
"""
Deep cluster analysis of Wikipedia medical article reading patterns.
Uses hierarchical clustering on the Jaccard similarity of each language's
top-50 article set (unified via Wikidata QIDs) to discover natural groupings.
Then characterises each cluster by its distinctive reading interests.
"""

import json
import os
import numpy as np
from collections import defaultdict, Counter
from itertools import combinations

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import squareform

WORK_DIR = "/sessions/modest-compassionate-cray"
OUTPUT_DIR = "/sessions/modest-compassionate-cray/mnt/outputs"

# Economist palette
ECO_RED = '#E3120B'
ECO_DARK = '#1A1A2E'
ECO_BLUE = '#006BA6'
ECO_LIGHT_BLUE = '#3EBCD2'
ECO_TEAL = '#00847E'
ECO_GREY = '#758D99'
ECO_LIGHT_GREY = '#D9E1E2'
ECO_BG = '#F7F5F0'
ECO_GRID = '#DAD5CC'
ECO_TEXT = '#333333'
ECO_SUBTITLE = '#666666'

CLUSTER_COLORS = ['#E3120B', '#006BA6', '#00847E', '#9B59B6', '#E67E22',
                  '#3EBCD2', '#2ECC71', '#F39C12', '#758D99', '#C0392B',
                  '#1ABC9C', '#8E44AD']

def economist_style(fig, ax, title, subtitle, source='Source: mdwiki.toolforge.org / Wikidata',
                    title_y=0.98, subtitle_y=None, pad_top=0.88):
    fig.patch.set_facecolor(ECO_BG)
    ax.set_facecolor(ECO_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(ECO_LIGHT_GREY)
    ax.spines['bottom'].set_color(ECO_LIGHT_GREY)
    ax.tick_params(colors=ECO_TEXT, labelsize=9)
    ax.tick_params(axis='x', length=0)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', color=ECO_GRID, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)
    fig.patches.append(mpatches.FancyBboxPatch(
        (0.02, 0.95), 0.12, 0.035, boxstyle="square,pad=0",
        facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
    fig.text(0.02, title_y - 0.06, title, fontsize=15, fontweight='bold',
             color=ECO_DARK, fontfamily='serif', ha='left', va='top', transform=fig.transFigure)
    if subtitle_y is None:
        subtitle_y = title_y - 0.06 - 0.055
    fig.text(0.02, subtitle_y, subtitle, fontsize=10, color=ECO_SUBTITLE,
             fontfamily='serif', ha='left', va='top', transform=fig.transFigure)
    fig.text(0.02, 0.01, source, fontsize=7, color=ECO_GREY,
             fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)
    plt.subplots_adjust(top=pad_top, bottom=0.08, left=0.15, right=0.95)

def economist_style_heatmap(fig, title, subtitle, source='Source: mdwiki.toolforge.org / Wikidata',
                            title_y=0.98, subtitle_y=None):
    fig.patch.set_facecolor(ECO_BG)
    fig.patches.append(mpatches.FancyBboxPatch(
        (0.02, 0.96), 0.08, 0.025, boxstyle="square,pad=0",
        facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
    fig.text(0.02, title_y - 0.05, title, fontsize=14, fontweight='bold',
             color=ECO_DARK, fontfamily='serif', ha='left', va='top', transform=fig.transFigure)
    if subtitle_y is None:
        subtitle_y = title_y - 0.05 - 0.05
    fig.text(0.02, subtitle_y, subtitle, fontsize=9.5, color=ECO_SUBTITLE,
             fontfamily='serif', ha='left', va='top', transform=fig.transFigure)
    fig.text(0.02, 0.01, source, fontsize=7, color=ECO_GREY,
             fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)

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

# Build QID sets per language
print("Building QID sets per language...")
lang_qids = {}  # lang -> set of QIDs
qid_labels = {} # QID -> en_label

for lang in all_articles:
    articles = all_articles[lang]
    wd = all_wikidata.get(lang, {})
    qids = set()
    for article in articles:
        title = article['title']
        wd_info = wd.get(title)
        if wd_info:
            qids.add(wd_info['qid'])
            if wd_info['en_label']:
                qid_labels[wd_info['qid']] = wd_info['en_label']
    lang_qids[lang] = qids

# Filter to languages with at least 20 articles matched
valid_langs = [l for l in lang_qids if len(lang_qids[l]) >= 20]
valid_langs.sort(key=lambda l: lang_info.get(l, {}).get('total', 0), reverse=True)
print(f"Languages with 20+ matched articles: {len(valid_langs)}")

# ============================================================
# COMPUTE JACCARD SIMILARITY MATRIX
# ============================================================
print("Computing Jaccard similarity matrix...")
n = len(valid_langs)
jaccard_sim = np.zeros((n, n))

for i in range(n):
    for j in range(n):
        if i == j:
            jaccard_sim[i, j] = 1.0
        else:
            s1 = lang_qids[valid_langs[i]]
            s2 = lang_qids[valid_langs[j]]
            inter = len(s1 & s2)
            union = len(s1 | s2)
            jaccard_sim[i, j] = inter / union if union > 0 else 0

# Convert to distance for clustering
jaccard_dist = 1 - jaccard_sim

# ============================================================
# HIERARCHICAL CLUSTERING
# ============================================================
print("Running hierarchical clustering...")
# Use only the upper triangle for scipy
condensed = squareform(jaccard_dist, checks=False)
Z = linkage(condensed, method='ward')

# Cut at a level that gives meaningful clusters (aim for ~6-10)
n_clusters = 8
cluster_labels = fcluster(Z, t=n_clusters, criterion='maxclust')

# Build cluster membership
clusters = defaultdict(list)
for i, lang in enumerate(valid_langs):
    clusters[cluster_labels[i]].append(lang)

# Language family metadata for context
LANG_FAMILIES = {
    # Germanic
    'en': 'Germanic', 'de': 'Germanic', 'nl': 'Germanic', 'sv': 'Germanic',
    'da': 'Germanic', 'no': 'Germanic', 'nn': 'Germanic', 'is': 'Germanic',
    'af': 'Germanic', 'lb': 'Germanic', 'fy': 'Germanic', 'yi': 'Germanic',
    'simple': 'Germanic',
    # Romance
    'es': 'Romance', 'fr': 'Romance', 'pt': 'Romance', 'it': 'Romance',
    'ro': 'Romance', 'ca': 'Romance', 'gl': 'Romance', 'oc': 'Romance',
    'an': 'Romance', 'ast': 'Romance', 'la': 'Romance',
    # Slavic
    'ru': 'Slavic', 'pl': 'Slavic', 'uk': 'Slavic', 'cs': 'Slavic',
    'sk': 'Slavic', 'sr': 'Slavic', 'hr': 'Slavic', 'bg': 'Slavic',
    'sl': 'Slavic', 'mk': 'Slavic', 'bs': 'Slavic', 'be': 'Slavic',
    'sh': 'Slavic',
    # Uralic
    'fi': 'Uralic', 'hu': 'Uralic', 'et': 'Uralic',
    # Semitic
    'ar': 'Semitic', 'he': 'Semitic',
    # Turkic
    'tr': 'Turkic', 'az': 'Turkic', 'kk': 'Turkic', 'uz': 'Turkic',
    'ky': 'Turkic', 'tt': 'Turkic', 'tk': 'Turkic',
    # Indo-Iranian
    'fa': 'Indo-Iranian', 'hi': 'Indo-Iranian', 'bn': 'Indo-Iranian',
    'ur': 'Indo-Iranian', 'pa': 'Indo-Iranian', 'ku': 'Indo-Iranian',
    'gu': 'Indo-Iranian', 'mr': 'Indo-Iranian', 'ne': 'Indo-Iranian',
    'si': 'Indo-Iranian', 'ps': 'Indo-Iranian', 'sd': 'Indo-Iranian',
    'ckb': 'Indo-Iranian', 'ta': 'Dravidian', 'te': 'Dravidian',
    'kn': 'Dravidian', 'ml': 'Dravidian',
    # Sino-Tibetan
    'zh': 'Sino-Tibetan', 'my': 'Sino-Tibetan',
    # Japonic / Koreanic
    'ja': 'Japonic', 'ko': 'Koreanic',
    # Austronesian
    'id': 'Austronesian', 'ms': 'Austronesian', 'tl': 'Austronesian',
    'ceb': 'Austronesian', 'war': 'Austronesian', 'jv': 'Austronesian',
    'su': 'Austronesian', 'min': 'Austronesian',
    # Tai-Kadai
    'th': 'Tai-Kadai',
    # Austroasiatic
    'vi': 'Austroasiatic', 'km': 'Austroasiatic',
    # Kartvelian
    'ka': 'Kartvelian',
    # Armenian
    'hy': 'Armenian',
    # Baltic
    'lt': 'Baltic', 'lv': 'Baltic',
    # Celtic
    'cy': 'Celtic', 'ga': 'Celtic', 'gd': 'Celtic', 'br': 'Celtic',
    # Albanian
    'sq': 'Albanian',
    # Hellenic
    'el': 'Hellenic',
    # Afroasiatic
    'am': 'Afroasiatic', 'so': 'Afroasiatic', 'ha': 'Afroasiatic',
    # Niger-Congo / Bantu
    'sw': 'Niger-Congo', 'yo': 'Niger-Congo', 'ig': 'Niger-Congo',
    'zu': 'Niger-Congo', 'rw': 'Niger-Congo', 'lg': 'Niger-Congo',
    'xh': 'Niger-Congo', 'sn': 'Niger-Congo',
    # Constructed
    'eo': 'Constructed',
}

LANG_NAMES_FULL = {
    'en': 'English', 'es': 'Spanish', 'de': 'German', 'ru': 'Russian',
    'fr': 'French', 'ja': 'Japanese', 'it': 'Italian', 'pt': 'Portuguese',
    'fa': 'Persian', 'pl': 'Polish', 'zh': 'Chinese', 'ar': 'Arabic',
    'nl': 'Dutch', 'sv': 'Swedish', 'uk': 'Ukrainian', 'cs': 'Czech',
    'tr': 'Turkish', 'he': 'Hebrew', 'id': 'Indonesian', 'fi': 'Finnish',
    'hu': 'Hungarian', 'ko': 'Korean', 'da': 'Danish', 'no': 'Norwegian',
    'ro': 'Romanian', 'vi': 'Vietnamese', 'th': 'Thai', 'el': 'Greek',
    'hi': 'Hindi', 'bn': 'Bengali', 'ca': 'Catalan', 'sr': 'Serbian',
    'hr': 'Croatian', 'bg': 'Bulgarian', 'sk': 'Slovak', 'sl': 'Slovenian',
    'et': 'Estonian', 'lt': 'Lithuanian', 'lv': 'Latvian', 'ms': 'Malay',
    'ka': 'Georgian', 'az': 'Azerbaijani', 'sq': 'Albanian', 'hy': 'Armenian',
    'mk': 'Macedonian', 'bs': 'Bosnian', 'gl': 'Galician', 'eu': 'Basque',
    'af': 'Afrikaans', 'ur': 'Urdu', 'ta': 'Tamil', 'te': 'Telugu',
    'kn': 'Kannada', 'ml': 'Malayalam', 'mr': 'Marathi', 'gu': 'Gujarati',
    'pa': 'Punjabi', 'ne': 'Nepali', 'si': 'Sinhala', 'my': 'Burmese',
    'km': 'Khmer', 'sw': 'Swahili', 'tl': 'Tagalog', 'eo': 'Esperanto',
    'simple': 'Simple English', 'sh': 'Serbo-Croatian', 'be': 'Belarusian',
    'cy': 'Welsh', 'ku': 'Kurdish', 'kk': 'Kazakh', 'uz': 'Uzbek',
    'ky': 'Kyrgyz', 'tt': 'Tatar',
}

# ============================================================
# PRINT CLUSTER ANALYSIS
# ============================================================
print(f"\n{'='*80}")
print(f"HIERARCHICAL CLUSTERING: {n_clusters} CLUSTERS")
print(f"{'='*80}")

cluster_info = {}

for cid in sorted(clusters.keys()):
    members = clusters[cid]
    # Family composition
    families = Counter(LANG_FAMILIES.get(l, 'Other') for l in members)
    top_families = families.most_common(3)

    # Find cluster's "signature" articles (most shared within cluster, less common outside)
    cluster_qids = Counter()
    for lang in members:
        for qid in lang_qids.get(lang, set()):
            cluster_qids[qid] += 1

    non_cluster_langs = [l for l in valid_langs if l not in members]
    non_cluster_qids = Counter()
    for lang in non_cluster_langs:
        for qid in lang_qids.get(lang, set()):
            non_cluster_qids[qid] += 1

    # Signature articles: high frequency in cluster, low outside (relative)
    signatures = []
    for qid, count_in in cluster_qids.items():
        freq_in = count_in / len(members)
        count_out = non_cluster_qids.get(qid, 0)
        freq_out = count_out / len(non_cluster_langs) if non_cluster_langs else 0
        if freq_in > 0.3:  # At least 30% of cluster
            lift = freq_in / (freq_out + 0.01)
            signatures.append((qid, qid_labels.get(qid, qid), freq_in, freq_out, lift))

    signatures.sort(key=lambda x: x[4], reverse=True)

    # Universal articles in cluster (>80% of members have them)
    universal = [(qid, qid_labels.get(qid, qid), count_in / len(members))
                 for qid, count_in in cluster_qids.items()
                 if count_in / len(members) >= 0.8]
    universal.sort(key=lambda x: x[2], reverse=True)

    member_names = [LANG_NAMES_FULL.get(l, l) for l in members[:15]]
    family_str = ', '.join([f"{f}({c})" for f, c in top_families])

    cluster_info[cid] = {
        'members': members,
        'families': families,
        'signatures': signatures[:20],
        'universal': universal[:20],
        'size': len(members)
    }

    print(f"\n--- CLUSTER {cid} ({len(members)} languages) ---")
    print(f"  Families: {family_str}")
    print(f"  Members: {', '.join(member_names)}")
    if len(members) > 15:
        print(f"    ... and {len(members)-15} more")
    print(f"  Signature articles (distinctive to this cluster):")
    for _, label, fi, fo, lift in signatures[:5]:
        print(f"    {label}: {fi:.0%} in cluster vs {fo:.0%} outside (lift={lift:.1f}x)")
    print(f"  Universal articles (>80% of cluster):")
    for _, label, freq in universal[:5]:
        print(f"    {label}: {freq:.0%}")


# ============================================================
# COMPUTE INTER-CLUSTER SIMILARITY
# ============================================================
print(f"\n{'='*80}")
print("INTER-CLUSTER SIMILARITY")
print(f"{'='*80}")

cluster_ids = sorted(clusters.keys())
n_c = len(cluster_ids)
inter_sim = np.zeros((n_c, n_c))

for i, c1 in enumerate(cluster_ids):
    for j, c2 in enumerate(cluster_ids):
        # Average Jaccard similarity between all pairs across clusters
        sims = []
        for l1 in clusters[c1]:
            idx1 = valid_langs.index(l1)
            for l2 in clusters[c2]:
                idx2 = valid_langs.index(l2)
                sims.append(jaccard_sim[idx1, idx2])
        inter_sim[i, j] = np.mean(sims)

for i, c1 in enumerate(cluster_ids):
    for j, c2 in enumerate(cluster_ids):
        if i < j:
            print(f"  Cluster {c1} <-> Cluster {c2}: avg Jaccard = {inter_sim[i,j]:.3f}")

# ============================================================
# NAME CLUSTERS BASED ON COMPOSITION
# ============================================================
cluster_names = {}
for cid in sorted(clusters.keys()):
    members = clusters[cid]
    families = Counter(LANG_FAMILIES.get(l, 'Other') for l in members)
    top_fam = families.most_common(1)[0][0]
    size = len(members)

    # Check specific compositions
    member_set = set(members)

    if 'en' in member_set and 'de' in member_set and 'fr' in member_set:
        cluster_names[cid] = 'Major European'
    elif top_fam == 'Slavic' and families['Slavic'] / size > 0.4:
        cluster_names[cid] = 'Slavic & Eastern European'
    elif top_fam == 'Romance' and families.get('Romance', 0) / size > 0.4:
        cluster_names[cid] = 'Romance'
    elif top_fam == 'Germanic' and families.get('Germanic', 0) / size > 0.4:
        cluster_names[cid] = 'Germanic & Nordic'
    elif ('ja' in member_set or 'zh' in member_set or 'ko' in member_set) and size <= 10:
        cluster_names[cid] = 'East Asian'
    elif ('ar' in member_set or 'fa' in member_set or 'ur' in member_set):
        if families.get('Indo-Iranian', 0) + families.get('Semitic', 0) + families.get('Turkic', 0) > size * 0.3:
            cluster_names[cid] = 'Middle Eastern & South Asian'
        else:
            cluster_names[cid] = f'Mixed ({top_fam}-led)'
    elif ('id' in member_set or 'ms' in member_set or 'vi' in member_set or 'th' in member_set):
        cluster_names[cid] = 'Southeast Asian'
    elif top_fam == 'Other' or families['Other'] / size > 0.5:
        cluster_names[cid] = 'Diverse / Smaller languages'
    else:
        cluster_names[cid] = f'{top_fam}-dominant'

    print(f"Cluster {cid}: {cluster_names[cid]} ({size} langs)")


# ============================================================
# FIGURE 8: Dendrogram (top 40 languages)
# ============================================================
print("\nGenerating Fig 8: Dendrogram...")

# Select top 40 languages by total views for a readable dendrogram
top40 = valid_langs[:40]
top40_idx = [valid_langs.index(l) for l in top40]

# Build sub-matrix
sub_dist = jaccard_dist[np.ix_(top40_idx, top40_idx)]
condensed_sub = squareform(sub_dist, checks=False)
Z_sub = linkage(condensed_sub, method='ward')

# Cluster label colours
sub_cluster_labels = [cluster_labels[valid_langs.index(l)] for l in top40]
color_map = {cid: CLUSTER_COLORS[i % len(CLUSTER_COLORS)] for i, cid in enumerate(sorted(set(sub_cluster_labels)))}
leaf_colors = {i: color_map[sub_cluster_labels[i]] for i in range(len(top40))}

fig, ax = plt.subplots(figsize=(10, 8))

dend = dendrogram(
    Z_sub,
    labels=[LANG_NAMES_FULL.get(l, l) for l in top40],
    orientation='right',
    leaf_font_size=8,
    color_threshold=0,
    above_threshold_color=ECO_GREY,
    ax=ax
)

# Color leaf labels by cluster
ylbls = ax.get_yticklabels()
for lbl in ylbls:
    lang_name = lbl.get_text()
    # Find which language this is
    for i, l in enumerate(top40):
        if LANG_NAMES_FULL.get(l, l) == lang_name:
            lbl.set_color(color_map[sub_cluster_labels[i]])
            lbl.set_fontfamily('serif')
            lbl.set_fontweight('bold')
            break

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_color(ECO_LIGHT_GREY)
ax.spines['left'].set_visible(False)
ax.tick_params(axis='x', colors=ECO_TEXT, labelsize=8)
ax.set_xlabel('Ward distance (Jaccard dissimilarity)', fontsize=9, fontfamily='serif', color=ECO_TEXT)

# Legend
legend_patches = []
for cid in sorted(cluster_names.keys()):
    if any(sub_cluster_labels[i] == cid for i in range(len(top40))):
        legend_patches.append(mpatches.Patch(color=color_map[cid], label=cluster_names[cid]))
ax.legend(handles=legend_patches, loc='lower right', fontsize=7, frameon=True,
          facecolor=ECO_BG, edgecolor=ECO_LIGHT_GREY, prop={'family': 'serif'})

economist_style_heatmap(fig,
    title='Languages that read alike, cluster together',
    subtitle='Hierarchical clustering of 40 largest Wikipedia language editions by\nJaccard similarity of their top-50 most-viewed medical articles.',
    title_y=0.995, subtitle_y=0.91)

plt.subplots_adjust(left=0.18, right=0.95, top=0.87, bottom=0.08)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig8_dendrogram.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig8")


# ============================================================
# FIGURE 9: Cluster composition by language family
# ============================================================
print("Generating Fig 9: Cluster composition...")

fig, ax = plt.subplots(figsize=(10, 5.5))

# Build stacked bar data
all_families = set()
for cid in cluster_info:
    all_families |= set(cluster_info[cid]['families'].keys())

# Limit to top families
family_totals = Counter()
for cid in cluster_info:
    for fam, count in cluster_info[cid]['families'].items():
        family_totals[fam] += count
top_families = [f for f, _ in family_totals.most_common(10)]
# Merge the rest into "Other"
if 'Other' not in top_families:
    top_families.append('Other')

family_colors = {
    'Germanic': '#006BA6', 'Romance': '#E3120B', 'Slavic': '#00847E',
    'Indo-Iranian': '#E67E22', 'Turkic': '#9B59B6', 'Uralic': '#3EBCD2',
    'Sino-Tibetan': '#F39C12', 'Austronesian': '#2ECC71', 'Semitic': '#C0392B',
    'Japonic': '#FF6B6B', 'Koreanic': '#A29BFE', 'Dravidian': '#FD79A8',
    'Other': '#758D99', 'Constructed': '#DFE6E9', 'Hellenic': '#74B9FF',
    'Baltic': '#55EFC4', 'Celtic': '#81ECEC', 'Albanian': '#B2BEC3',
    'Armenian': '#636E72', 'Kartvelian': '#FDCB6E', 'Tai-Kadai': '#E17055',
    'Austroasiatic': '#00CEC9', 'Niger-Congo': '#6C5CE7', 'Afroasiatic': '#D63031',
}

cluster_order = sorted(cluster_names.keys(), key=lambda c: cluster_info[c]['size'], reverse=True)
x_labels = [f"{cluster_names[c]}\n({cluster_info[c]['size']})" for c in cluster_order]
x_pos = np.arange(len(cluster_order))

bottom = np.zeros(len(cluster_order))

for fam in top_families:
    vals = []
    for cid in cluster_order:
        count = cluster_info[cid]['families'].get(fam, 0)
        # Also aggregate small families into Other
        if fam == 'Other':
            count = sum(v for k, v in cluster_info[cid]['families'].items() if k not in top_families or k == 'Other')
        vals.append(count)
    vals = np.array(vals, dtype=float)
    if vals.sum() > 0:
        ax.bar(x_pos, vals, bottom=bottom, label=fam, width=0.65,
               color=family_colors.get(fam, '#95A5A6'), edgecolor='white', linewidth=0.5)
        bottom += vals

ax.set_xticks(x_pos)
ax.set_xticklabels(x_labels, fontsize=7.5, fontfamily='serif', color=ECO_TEXT)
ax.set_ylabel('')
ax.legend(fontsize=7, ncol=3, loc='upper right', frameon=True,
          facecolor=ECO_BG, edgecolor=ECO_LIGHT_GREY, prop={'family': 'serif'})

economist_style(fig, ax,
    title='Reading clusters mirror language families',
    subtitle='Composition of each reading-pattern cluster by language family.\nNumber in parentheses = languages in cluster.',
    title_y=0.99, subtitle_y=0.885, pad_top=0.84)

plt.subplots_adjust(left=0.08, right=0.95, top=0.84, bottom=0.14)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig9_cluster_composition.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig9")


# ============================================================
# FIGURE 10: Distinctive articles per cluster
# ============================================================
print("Generating Fig 10: Cluster signature articles...")

# Pick the 4 most interesting/large clusters
show_clusters = sorted(cluster_names.keys(), key=lambda c: cluster_info[c]['size'], reverse=True)[:6]

fig, axes = plt.subplots(2, 3, figsize=(14, 10))
axes = axes.flatten()

for idx, cid in enumerate(show_clusters):
    ax = axes[idx]
    ax.set_facecolor(ECO_BG)

    sigs = cluster_info[cid]['signatures'][:8]
    if not sigs:
        ax.text(0.5, 0.5, 'No distinctive\narticles', transform=ax.transAxes,
                ha='center', va='center', fontsize=10, color=ECO_GREY, fontfamily='serif')
        ax.set_title(f'{cluster_names[cid]}', fontsize=10, fontfamily='serif',
                     fontweight='bold', color=CLUSTER_COLORS[idx % len(CLUSTER_COLORS)])
        ax.axis('off')
        continue

    labels = [s[1][:28] for s in sigs]
    lifts = [s[4] for s in sigs]
    freq_in = [s[2] for s in sigs]

    color = CLUSTER_COLORS[idx % len(CLUSTER_COLORS)]
    bars = ax.barh(range(len(labels)), lifts, color=color, height=0.65,
                   edgecolor='white', alpha=0.85)

    for i, (bar, lift, fi) in enumerate(zip(bars, lifts, freq_in)):
        ax.text(bar.get_width() + 0.1, i,
                f'{lift:.1f}x ({fi:.0%})', va='center', fontsize=6.5,
                color=ECO_TEXT, fontfamily='serif')

    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7, fontfamily='serif', color=ECO_TEXT)
    ax.invert_yaxis()
    ax.set_title(f'{cluster_names[cid]} ({cluster_info[cid]["size"]} langs)',
                 fontsize=9, fontfamily='serif', fontweight='bold', color=color, pad=6)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color(ECO_LIGHT_GREY)
    ax.tick_params(length=0, labelsize=7)
    ax.grid(axis='x', color=ECO_GRID, linewidth=0.3, alpha=0.5)

fig.patch.set_facecolor(ECO_BG)
fig.patches.append(mpatches.FancyBboxPatch(
    (0.02, 0.98), 0.08, 0.02, boxstyle="square,pad=0",
    facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
fig.text(0.02, 0.965, 'What makes each cluster unique',
         fontsize=15, fontweight='bold', color=ECO_DARK, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.930, 'Distinctive articles per cluster: "lift" measures how much more likely\nan article is to be in this cluster\'s top 50 vs. outside it. Percentage = cluster coverage.',
         fontsize=9.5, color=ECO_SUBTITLE, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.01, 'Source: mdwiki.toolforge.org / Wikidata', fontsize=7,
         color=ECO_GREY, fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)

plt.subplots_adjust(top=0.87, bottom=0.05, left=0.10, right=0.96, hspace=0.45, wspace=0.45)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig10_cluster_signatures.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig10")


# ============================================================
# FIGURE 11: Inter-cluster similarity heatmap
# ============================================================
print("Generating Fig 11: Inter-cluster similarity...")

fig, ax = plt.subplots(figsize=(8, 7))

eco_blue_cmap = LinearSegmentedColormap.from_list('eco_blue',
    ['#F7F5F0', '#B8D4E3', '#006BA6', '#003F5C'], N=256)

ordered = sorted(cluster_names.keys(), key=lambda c: cluster_info[c]['size'], reverse=True)
ordered_idx = [cluster_ids.index(c) for c in ordered]
reordered_sim = inter_sim[np.ix_(ordered_idx, ordered_idx)]
cnames = [f"{cluster_names[c]}\n({cluster_info[c]['size']})" for c in ordered]

im = ax.imshow(reordered_sim, cmap=eco_blue_cmap, aspect='equal', vmin=0, vmax=0.5)

for i in range(len(ordered)):
    for j in range(len(ordered)):
        val = reordered_sim[i, j]
        text_color = 'white' if val > 0.3 else ECO_DARK
        ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                fontsize=7.5, fontfamily='serif', color=text_color, fontweight='bold')

ax.set_xticks(range(len(cnames)))
ax.set_xticklabels(cnames, fontsize=7, fontfamily='serif', color=ECO_TEXT, rotation=45, ha='right')
ax.set_yticks(range(len(cnames)))
ax.set_yticklabels(cnames, fontsize=7, fontfamily='serif', color=ECO_TEXT)

for i in range(len(ordered)+1):
    ax.axhline(i-0.5, color='white', linewidth=0.5)
    ax.axvline(i-0.5, color='white', linewidth=0.5)
ax.tick_params(length=0)

cbar = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
cbar.set_label('Avg. Jaccard similarity', fontsize=8, fontfamily='serif', color=ECO_TEXT)
cbar.ax.tick_params(labelsize=7)

economist_style_heatmap(fig,
    title='How similar are the reading clusters?',
    subtitle='Average Jaccard similarity between language clusters. Higher = more\noverlap in top-50 medical articles. Diagonal = within-cluster similarity.',
    title_y=0.995, subtitle_y=0.91)

plt.subplots_adjust(left=0.20, right=0.88, top=0.87, bottom=0.18)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig11_cluster_similarity.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig11")


# ============================================================
# SAVE DATA
# ============================================================
print("\nSaving cluster analysis data...")

cluster_export = {
    'n_clusters': n_clusters,
    'n_languages_clustered': len(valid_langs),
    'clusters': {}
}

for cid in sorted(clusters.keys()):
    cluster_export['clusters'][str(cid)] = {
        'name': cluster_names[cid],
        'size': cluster_info[cid]['size'],
        'members': clusters[cid],
        'family_composition': dict(cluster_info[cid]['families']),
        'signature_articles': [
            {'qid': s[0], 'en_label': s[1], 'freq_in_cluster': round(s[2], 3),
             'freq_outside': round(s[3], 3), 'lift': round(s[4], 2)}
            for s in cluster_info[cid]['signatures'][:15]
        ],
        'universal_articles': [
            {'qid': u[0], 'en_label': u[1], 'coverage': round(u[2], 3)}
            for u in cluster_info[cid]['universal'][:15]
        ]
    }

with open(os.path.join(OUTPUT_DIR, 'cluster_analysis.json'), 'w') as f:
    json.dump(cluster_export, f, ensure_ascii=False, indent=2)

print(f"\n{'='*60}")
print("CLUSTER ANALYSIS COMPLETE")
print(f"{'='*60}")
