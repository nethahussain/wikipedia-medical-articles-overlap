#!/usr/bin/env python3
"""
Generate Economist-style time-trend visualisations for Wikipedia medical article pageviews.
Uses year-by-year data (2016-2025) from mdwiki.toolforge.org.
"""

import json, os
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

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

LINE_COLORS = ['#E3120B', '#006BA6', '#00847E', '#9B59B6', '#E67E22',
               '#3EBCD2', '#2ECC71', '#F39C12', '#C0392B', '#1ABC9C',
               '#34495E', '#D35400']

YEARS = list(range(2016, 2026))
YEAR_LABELS = [str(y) for y in YEARS]

# ── Load data ──
print("Loading time-series data...")
with open(os.path.join(WORK_DIR, "timeseries_data.json")) as f:
    ts = json.load(f)

lang_yearly = ts['lang_yearly']
article_ts = ts['article_timeseries']

# Load Wikidata for label mapping
with open(os.path.join(WORK_DIR, "all_wikidata.json")) as f:
    all_wikidata = json.load(f)


def economist_header(fig, title, subtitle, title_y=0.98, subtitle_y=None, pad_top=0.88):
    """Apply Economist styling to a figure with proper spacing."""
    fig.patch.set_facecolor(ECO_BG)
    # Red accent bar
    fig.patches.append(mpatches.FancyBboxPatch(
        (0.02, 0.96), 0.10, 0.028, boxstyle="square,pad=0",
        facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
    # Title
    fig.text(0.02, title_y - 0.06, title,
             fontsize=15, fontweight='bold', color=ECO_DARK, fontfamily='serif',
             ha='left', va='top', transform=fig.transFigure)
    # Subtitle
    if subtitle_y is None:
        subtitle_y = title_y - 0.06 - 0.055
    fig.text(0.02, subtitle_y, subtitle,
             fontsize=10, color=ECO_SUBTITLE, fontfamily='serif',
             ha='left', va='top', transform=fig.transFigure)
    # Source
    fig.text(0.02, 0.01, 'Source: mdwiki.toolforge.org / Wikidata',
             fontsize=7, color=ECO_GREY, fontfamily='serif',
             ha='left', va='bottom', transform=fig.transFigure)


def style_ax(ax):
    """Style a single axes in Economist fashion."""
    ax.set_facecolor(ECO_BG)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(ECO_LIGHT_GREY)
    ax.spines['bottom'].set_color(ECO_LIGHT_GREY)
    ax.tick_params(colors=ECO_TEXT, labelsize=8.5)
    ax.tick_params(axis='x', length=0)
    ax.tick_params(axis='y', length=0)
    ax.grid(axis='y', color=ECO_GRID, linewidth=0.5, alpha=0.7)
    ax.set_axisbelow(True)


def billions(x, _):
    if x >= 1e9: return f'{x/1e9:.1f}B'
    if x >= 1e6: return f'{x/1e6:.0f}M'
    if x >= 1e3: return f'{x/1e3:.0f}K'
    return str(int(x))


# ======================================================================
# FIGURE 12: Global medical pageview trends (aggregate)
# ======================================================================
print("Generating Fig 12: Global aggregate trend...")

# Sum across all languages per year
global_yearly = np.zeros(len(YEARS))
for lang, info in lang_yearly.items():
    for i, y in enumerate(YEAR_LABELS):
        global_yearly[i] += info['yearly'].get(y, 0)

fig, ax = plt.subplots(figsize=(10, 5.5))
style_ax(ax)

ax.fill_between(YEARS, global_yearly, alpha=0.15, color=ECO_RED)
ax.plot(YEARS, global_yearly, color=ECO_RED, linewidth=2.5, marker='o', markersize=6,
        markerfacecolor='white', markeredgecolor=ECO_RED, markeredgewidth=2, zorder=5)

# Annotate key points
peak_idx = np.argmax(global_yearly)
ax.annotate(f'{global_yearly[peak_idx]/1e9:.1f}B',
            xy=(YEARS[peak_idx], global_yearly[peak_idx]),
            xytext=(0, 14), textcoords='offset points',
            fontsize=9, fontweight='bold', color=ECO_RED, fontfamily='serif',
            ha='center')

# 2020 COVID label
idx_2020 = YEARS.index(2020)
ax.annotate('COVID-19\npandemic',
            xy=(2020, global_yearly[idx_2020]),
            xytext=(30, 20), textcoords='offset points',
            fontsize=8, color=ECO_SUBTITLE, fontfamily='serif',
            ha='left', va='bottom',
            arrowprops=dict(arrowstyle='->', color=ECO_GREY, lw=1))

ax.set_xticks(YEARS)
ax.set_xticklabels(YEAR_LABELS, fontfamily='serif')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(billions))
ax.set_ylabel('')

economist_header(fig,
    title='Medical Wikipedia pageviews peaked during the pandemic',
    subtitle='Total annual pageviews of medical articles across all 337 Wikipedia language editions, 2016\u20132025.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.84)
plt.subplots_adjust(top=0.84, bottom=0.10, left=0.10, right=0.95)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig12_global_trend.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig12")


# ======================================================================
# FIGURE 13: Top 10 languages trend lines
# ======================================================================
print("Generating Fig 13: Top languages trends...")

# Pick top 10 by total views
top10 = sorted(lang_yearly.items(), key=lambda x: x[1]['total'], reverse=True)[:10]

fig, ax = plt.subplots(figsize=(10, 6))
style_ax(ax)

LANG_NAMES = {
    'en': 'English', 'es': 'Spanish', 'de': 'German', 'ru': 'Russian',
    'fr': 'French', 'ja': 'Japanese', 'it': 'Italian', 'pt': 'Portuguese',
    'fa': 'Persian', 'pl': 'Polish', 'zh': 'Chinese', 'ar': 'Arabic',
    'nl': 'Dutch', 'sv': 'Swedish', 'uk': 'Ukrainian'
}

for i, (lang, info) in enumerate(top10):
    vals = [info['yearly'].get(y, 0) for y in YEAR_LABELS]
    color = LINE_COLORS[i % len(LINE_COLORS)]
    lw = 2.5 if i == 0 else 1.5
    ax.plot(YEARS, vals, color=color, linewidth=lw, label=LANG_NAMES.get(lang, lang),
            marker='o' if i < 3 else None, markersize=4, markerfacecolor='white',
            markeredgecolor=color, markeredgewidth=1.5, alpha=0.9)
    # Label at end
    ax.text(2025.15, vals[-1], LANG_NAMES.get(lang, lang),
            fontsize=7, color=color, fontfamily='serif', va='center', fontweight='bold')

ax.set_xticks(YEARS)
ax.set_xticklabels(YEAR_LABELS, fontfamily='serif')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(billions))
ax.set_xlim(2015.8, 2026.5)

economist_header(fig,
    title='English dominates, but trends differ by language',
    subtitle='Annual medical article pageviews for the ten largest Wikipedia language editions, 2016\u20132025.\nNote: English dwarfs all others; secondary axis would obscure relative trends.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.84)
plt.subplots_adjust(top=0.84, bottom=0.10, left=0.10, right=0.82)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig13_top10_lang_trends.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig13")


# ======================================================================
# FIGURE 14: Non-English languages indexed to 2016 = 100
# ======================================================================
print("Generating Fig 14: Indexed growth (non-English)...")

# Pick diverse set excluding English
growth_langs = ['es', 'de', 'ru', 'fr', 'ja', 'ar', 'hi', 'id', 'vi', 'tr', 'bn', 'fa']
growth_langs = [l for l in growth_langs if l in lang_yearly]

fig, ax = plt.subplots(figsize=(10, 6))
style_ax(ax)

# 100 baseline
ax.axhline(100, color=ECO_GREY, linewidth=1, linestyle='--', alpha=0.5)
ax.text(2015.9, 102, 'Baseline (2016)', fontsize=7, color=ECO_GREY, fontfamily='serif')

for i, lang in enumerate(growth_langs):
    info = lang_yearly[lang]
    vals = [info['yearly'].get(y, 0) for y in YEAR_LABELS]
    base = vals[0] if vals[0] > 0 else 1
    indexed = [(v / base) * 100 for v in vals]
    color = LINE_COLORS[i % len(LINE_COLORS)]
    ax.plot(YEARS, indexed, color=color, linewidth=1.8, label=LANG_NAMES.get(lang, lang),
            alpha=0.85)
    ax.text(2025.15, indexed[-1], LANG_NAMES.get(lang, lang),
            fontsize=7, color=color, fontfamily='serif', va='center', fontweight='bold')

ax.set_xticks(YEARS)
ax.set_xticklabels(YEAR_LABELS, fontfamily='serif')
ax.set_ylabel('Index (2016 = 100)', fontsize=9, fontfamily='serif', color=ECO_TEXT)
ax.set_xlim(2015.8, 2026.8)

economist_header(fig,
    title='Hindi and Bengali surged; European languages faded',
    subtitle='Medical article pageviews indexed to 2016 = 100 for selected non-English Wikipedias.\nValues above 100 indicate growth relative to 2016.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.84)
plt.subplots_adjust(top=0.84, bottom=0.10, left=0.10, right=0.82)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig14_indexed_growth.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig14")


# ======================================================================
# FIGURE 15: COVID bump - 2019 vs 2020 by language
# ======================================================================
print("Generating Fig 15: COVID bump by language...")

# Calculate % change 2019->2020 for top 20 languages
covid_bump = []
for lang, info in lang_yearly.items():
    v2019 = info['yearly'].get('2019', 0)
    v2020 = info['yearly'].get('2020', 0)
    if v2019 > 1e6:  # meaningful volume
        pct = ((v2020 - v2019) / v2019) * 100
        covid_bump.append((lang, pct, v2020))

covid_bump.sort(key=lambda x: x[1], reverse=True)
top_bump = covid_bump[:20]

fig, ax = plt.subplots(figsize=(10, 7))
style_ax(ax)

langs_b = [LANG_NAMES.get(x[0], x[0]) for x in top_bump]
pcts_b = [x[1] for x in top_bump]
colors_b = [ECO_RED if p > 0 else ECO_BLUE for p in pcts_b]

bars = ax.barh(range(len(langs_b)), pcts_b, color=colors_b, height=0.65, alpha=0.85,
               edgecolor='white', linewidth=0.5)

for i, (bar, pct) in enumerate(zip(bars, pcts_b)):
    ax.text(bar.get_width() + 1, i, f'+{pct:.0f}%', va='center',
            fontsize=7.5, color=ECO_TEXT, fontfamily='serif', fontweight='bold')

ax.set_yticks(range(len(langs_b)))
ax.set_yticklabels(langs_b, fontsize=8, fontfamily='serif', color=ECO_TEXT)
ax.invert_yaxis()
ax.set_xlabel('')
ax.axvline(0, color=ECO_DARK, linewidth=0.8)

economist_header(fig,
    title='The pandemic sent medical Wikipedia traffic soaring',
    subtitle='Percentage change in medical article pageviews from 2019 to 2020, for the 20\nlanguages with the largest increase. Only languages with >1M views in 2019 included.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.84)
plt.subplots_adjust(top=0.84, bottom=0.06, left=0.16, right=0.92)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig15_covid_bump.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig15")


# ======================================================================
# FIGURE 16: Article-level trends — universals (Heart, HIV/AIDS, COVID-19, TB)
# ======================================================================
print("Generating Fig 16: Key article trends across languages...")

# For each target article, sum its yearly views across all languages we have
FOCUS_ARTICLES = {
    'COVID-19': ['COVID-19'],
    'HIV/AIDS': ['HIV/AIDS', 'VIH/sida', 'HIV/Aids', 'ВИЧ/СПИД'],
    'Tuberculosis': ['Tuberculosis', 'Tuberkulose', 'Tuberculose', 'Туберкулёз'],
    'Schizophrenia': ['Schizophrenia', 'Schizophrénie', 'Schizophrenie', 'Шизофрения'],
    'Diabetes': ['Diabetes mellitus', 'Diabetes', 'Diabète'],
    'Cancer': ['Cancer', 'Krebs (Medizin)', 'Cancer (maladie)', 'Рак (заболевание)'],
}

# Build title -> en_label mapping from Wikidata
title_to_concept = {}
for lang in article_ts:
    wd = all_wikidata.get(lang, {})
    for title in article_ts[lang]:
        wd_info = wd.get(title)
        if wd_info and wd_info.get('en_label'):
            title_to_concept[f"{lang}:{title}"] = wd_info['en_label']

# Aggregate by concept
concept_yearly = {}
for lang, articles in article_ts.items():
    wd = all_wikidata.get(lang, {})
    for title, yearly in articles.items():
        wd_info = wd.get(title)
        if wd_info and wd_info.get('en_label'):
            label = wd_info['en_label']
            if label not in concept_yearly:
                concept_yearly[label] = np.zeros(len(YEARS))
            for i, y in enumerate(YEAR_LABELS):
                concept_yearly[label][i] += yearly.get(y, 0)

# Pick 6 interesting articles with clear trends
TREND_ARTICLES = ['COVID-19', 'HIV/AIDS', 'Tuberculosis', 'Schizophrenia', 'Diabetes', 'Cancer']
TREND_ARTICLES = [a for a in TREND_ARTICLES if a in concept_yearly]

fig, axes = plt.subplots(2, 3, figsize=(14, 8))
axes = axes.flatten()

for idx, concept in enumerate(TREND_ARTICLES[:6]):
    ax = axes[idx]
    style_ax(ax)
    vals = concept_yearly[concept]

    ax.fill_between(YEARS, vals, alpha=0.12, color=LINE_COLORS[idx])
    ax.plot(YEARS, vals, color=LINE_COLORS[idx], linewidth=2, marker='o',
            markersize=4, markerfacecolor='white', markeredgecolor=LINE_COLORS[idx],
            markeredgewidth=1.5)

    ax.set_title(concept, fontsize=10, fontweight='bold', fontfamily='serif',
                 color=LINE_COLORS[idx], pad=8)
    ax.set_xticks(YEARS[::2])
    ax.set_xticklabels([str(y) for y in YEARS[::2]], fontsize=7, fontfamily='serif')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(billions))

    # Peak annotation
    peak_i = np.argmax(vals)
    ax.annotate(f'{billions(vals[peak_i], None)}',
                xy=(YEARS[peak_i], vals[peak_i]),
                xytext=(0, 10), textcoords='offset points',
                fontsize=7.5, fontweight='bold', color=LINE_COLORS[idx],
                fontfamily='serif', ha='center')

fig.patch.set_facecolor(ECO_BG)
fig.patches.append(mpatches.FancyBboxPatch(
    (0.02, 0.98), 0.08, 0.02, boxstyle="square,pad=0",
    facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
fig.text(0.02, 0.955, 'Different diseases, different trajectories',
         fontsize=15, fontweight='bold', color=ECO_DARK, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.918, 'Annual pageviews for six key medical topics, summed across 24 Wikipedia language editions, 2016\u20132025.',
         fontsize=10, color=ECO_SUBTITLE, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.01, 'Source: mdwiki.toolforge.org / Wikidata', fontsize=7,
         color=ECO_GREY, fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)
plt.subplots_adjust(top=0.88, bottom=0.08, left=0.07, right=0.96, hspace=0.45, wspace=0.30)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig16_article_trends.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig16")


# ======================================================================
# FIGURE 17: COVID-19 article emergence - small multiples by language
# ======================================================================
print("Generating Fig 17: COVID-19 by language...")

# Find COVID-19 article in each language
covid_by_lang = {}
for lang, articles in article_ts.items():
    wd = all_wikidata.get(lang, {})
    for title, yearly in articles.items():
        wd_info = wd.get(title)
        if wd_info and wd_info.get('en_label') == 'COVID-19':
            covid_by_lang[lang] = yearly
        elif wd_info and wd_info.get('en_label') == 'COVID-19 pandemic':
            if lang not in covid_by_lang:
                covid_by_lang[lang] = yearly

# Pick top 12 by peak views
covid_sorted = sorted(covid_by_lang.items(),
                      key=lambda x: max(x[1].get(y, 0) for y in YEAR_LABELS),
                      reverse=True)[:12]

fig, axes = plt.subplots(3, 4, figsize=(14, 8.5))
axes = axes.flatten()

for idx, (lang, yearly) in enumerate(covid_sorted):
    ax = axes[idx]
    style_ax(ax)
    vals = [yearly.get(y, 0) for y in YEAR_LABELS]
    ax.fill_between(YEARS, vals, alpha=0.2, color=ECO_RED)
    ax.plot(YEARS, vals, color=ECO_RED, linewidth=1.8)
    ax.set_title(LANG_NAMES.get(lang, lang), fontsize=9, fontweight='bold',
                 fontfamily='serif', color=ECO_DARK, pad=5)
    ax.set_xticks([2016, 2020, 2025])
    ax.set_xticklabels(['16', '20', '25'], fontsize=7, fontfamily='serif')
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(billions))
    ax.tick_params(labelsize=6.5)

fig.patch.set_facecolor(ECO_BG)
fig.patches.append(mpatches.FancyBboxPatch(
    (0.02, 0.98), 0.08, 0.02, boxstyle="square,pad=0",
    facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
fig.text(0.02, 0.955, 'COVID-19 hit every language at once',
         fontsize=15, fontweight='bold', color=ECO_DARK, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.918, 'Annual pageviews for COVID-19 articles across 12 Wikipedia language editions, 2016\u20132025.\nNote different y-axis scales reflecting each edition\u2019s readership size.',
         fontsize=10, color=ECO_SUBTITLE, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.01, 'Source: mdwiki.toolforge.org / Wikidata', fontsize=7,
         color=ECO_GREY, fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)
plt.subplots_adjust(top=0.87, bottom=0.06, left=0.06, right=0.96, hspace=0.55, wspace=0.30)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig17_covid_by_language.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig17")


# ======================================================================
# FIGURE 18: Share shift - mental health vs infectious disease over time
# ======================================================================
print("Generating Fig 18: Category share shift over time...")

# Classify articles into categories
MENTAL_HEALTH = {'Schizophrenia', 'Bipolar disorder', 'Autism', 'Asperger syndrome',
                 'Depression', 'Major depressive disorder', 'Anxiety disorder',
                 'Attention deficit hyperactivity disorder', 'Obsessive\u2013compulsive disorder',
                 'Tourette syndrome', 'Post-traumatic stress disorder',
                 'Borderline personality disorder', 'Anorexia nervosa', 'MDMA',
                 'Substance dependence', 'Dissociative identity disorder'}

INFECTIOUS = {'HIV/AIDS', 'Tuberculosis', 'Malaria', 'Dengue fever', 'Cholera',
              'Typhoid fever', 'Ebola', 'Influenza', 'Pneumonia', 'Hepatitis B',
              'Hepatitis A', 'Measles', 'COVID-19', 'COVID-19 pandemic',
              'Chickenpox', 'Meningitis', 'Rabies', 'Whooping cough',
              'Spanish flu', 'Infectious mononucleosis'}

CANCER = {'Cancer', 'Breast cancer', 'Lung cancer', 'Prostate cancer', 'Leukemia',
          'Colorectal cancer', 'Pancreatic cancer', 'Lymphoma', 'Brain tumor'}

cat_yearly = {
    'Mental health': np.zeros(len(YEARS)),
    'Infectious disease': np.zeros(len(YEARS)),
    'Cancer': np.zeros(len(YEARS)),
}

for concept, vals in concept_yearly.items():
    if concept in MENTAL_HEALTH:
        cat_yearly['Mental health'] += vals
    elif concept in INFECTIOUS:
        cat_yearly['Infectious disease'] += vals
    elif concept in CANCER:
        cat_yearly['Cancer'] += vals

# Compute total per year across all concepts
total_per_year = np.zeros(len(YEARS))
for vals in concept_yearly.values():
    total_per_year += vals
total_per_year = np.maximum(total_per_year, 1)

fig, ax = plt.subplots(figsize=(10, 5.5))
style_ax(ax)

cat_colors = {'Mental health': ECO_BLUE, 'Infectious disease': ECO_RED, 'Cancer': ECO_TEAL}
for cat, vals in cat_yearly.items():
    share = (vals / total_per_year) * 100
    ax.plot(YEARS, share, color=cat_colors[cat], linewidth=2.5, label=cat,
            marker='o', markersize=5, markerfacecolor='white',
            markeredgecolor=cat_colors[cat], markeredgewidth=1.8)
    ax.text(2025.15, share[-1], cat, fontsize=8, color=cat_colors[cat],
            fontfamily='serif', va='center', fontweight='bold')

ax.set_xticks(YEARS)
ax.set_xticklabels(YEAR_LABELS, fontfamily='serif')
ax.set_ylabel('Share of total views (%)', fontsize=9, fontfamily='serif', color=ECO_TEXT)
ax.set_xlim(2015.8, 2027.5)
ax.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=0))

economist_header(fig,
    title='Infectious diseases dominate, but mental health\u2019s share is growing',
    subtitle='Each category\u2019s share of total medical article pageviews across 24 Wikipedia editions, 2016\u20132025.\nCOVID-19 is included in the infectious disease category.',
    title_y=0.99, subtitle_y=0.875, pad_top=0.84)
plt.subplots_adjust(top=0.84, bottom=0.10, left=0.10, right=0.80)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig18_category_share_shift.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig18")


# ======================================================================
# FIGURE 19: Heatmap — year-over-year growth by language
# ======================================================================
print("Generating Fig 19: YoY growth heatmap...")

from matplotlib.colors import TwoSlopeNorm

# Top 20 languages by total
top20_langs = sorted(lang_yearly.items(), key=lambda x: x[1]['total'], reverse=True)[:20]
top20_codes = [x[0] for x in top20_langs]

# Build growth matrix (year-over-year % change)
growth_matrix = np.zeros((len(top20_codes), len(YEARS) - 1))
for i, lang in enumerate(top20_codes):
    info = lang_yearly[lang]
    for j in range(len(YEARS) - 1):
        prev = info['yearly'].get(YEAR_LABELS[j], 0)
        curr = info['yearly'].get(YEAR_LABELS[j + 1], 0)
        if prev > 0:
            growth_matrix[i, j] = ((curr - prev) / prev) * 100
        else:
            growth_matrix[i, j] = 0

fig, ax = plt.subplots(figsize=(10, 7))

norm = TwoSlopeNorm(vmin=-40, vcenter=0, vmax=60)
from matplotlib.colors import LinearSegmentedColormap
div_cmap = LinearSegmentedColormap.from_list('eco_div',
    ['#006BA6', '#B8D4E3', '#F7F5F0', '#F5B7B1', '#E3120B'], N=256)

im = ax.imshow(growth_matrix, cmap=div_cmap, norm=norm, aspect='auto')

# Labels
ax.set_xticks(range(len(YEARS) - 1))
ax.set_xticklabels([f'{YEAR_LABELS[j]}\u2013{YEAR_LABELS[j+1][2:]}' for j in range(len(YEARS)-1)],
                    fontsize=7.5, fontfamily='serif', rotation=45, ha='right', color=ECO_TEXT)
ax.set_yticks(range(len(top20_codes)))
ax.set_yticklabels([LANG_NAMES.get(l, l) for l in top20_codes],
                    fontsize=8, fontfamily='serif', color=ECO_TEXT)

# Values in cells
for i in range(len(top20_codes)):
    for j in range(len(YEARS) - 1):
        val = growth_matrix[i, j]
        text_color = 'white' if abs(val) > 25 else ECO_DARK
        ax.text(j, i, f'{val:+.0f}%', ha='center', va='center',
                fontsize=6.5, fontfamily='serif', color=text_color, fontweight='bold')

# Grid
for i in range(len(top20_codes) + 1):
    ax.axhline(i - 0.5, color='white', linewidth=0.5)
for j in range(len(YEARS)):
    ax.axvline(j - 0.5, color='white', linewidth=0.5)

ax.tick_params(length=0)
cbar = fig.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
cbar.set_label('Year-over-year change (%)', fontsize=8, fontfamily='serif', color=ECO_TEXT)
cbar.ax.tick_params(labelsize=7)

fig.patch.set_facecolor(ECO_BG)
fig.patches.append(mpatches.FancyBboxPatch(
    (0.02, 0.97), 0.08, 0.02, boxstyle="square,pad=0",
    facecolor=ECO_RED, edgecolor='none', transform=fig.transFigure, zorder=10))
fig.text(0.02, 0.945, 'The pandemic spike was universal, but recovery varies',
         fontsize=14, fontweight='bold', color=ECO_DARK, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.905, 'Year-over-year percentage change in medical article pageviews for the 20 largest Wikipedia editions.\nRed = growth, blue = decline.',
         fontsize=9.5, color=ECO_SUBTITLE, fontfamily='serif',
         ha='left', va='top', transform=fig.transFigure)
fig.text(0.02, 0.01, 'Source: mdwiki.toolforge.org / Wikidata', fontsize=7,
         color=ECO_GREY, fontfamily='serif', ha='left', va='bottom', transform=fig.transFigure)
plt.subplots_adjust(top=0.86, bottom=0.12, left=0.12, right=0.90)
fig.savefig(os.path.join(OUTPUT_DIR, 'eco_fig19_yoy_growth_heatmap.png'), dpi=150, facecolor=ECO_BG)
plt.close()
print("  Saved eco_fig19")


print("\n" + "=" * 60)
print("ALL TREND CHARTS COMPLETE")
print("=" * 60)
