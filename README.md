# Wikipedia Medical Articles: Cross-Language Overlap Analysis

**Research question:** What are the top 50 most-read medical articles across all 337 Wikipedia language editions, and how much overlap exists between them?

This project analyzes pageview data from [WikiProject Medicine](https://mdwiki.toolforge.org/views/index.php?sub_dir=users-agents) to find the most universally read medical articles across all Wikipedia languages. It uses [Wikidata](https://www.wikidata.org/) to unify article identities across languages, enabling direct comparison of reading interests worldwide.

## Key Findings

> ### [**Explore the Top 50 Medical Articles Across All Wikipedias** &#x1F310;](https://nethahussain.github.io/wikipedia-medical-articles-overlap/top50_medical_articles.html)
> Interactive table with search, sorting, and per-language breakdowns — click to open directly in your browser.

- **1,929 unique medical articles** appear in the top 50 of at least one language edition
- **865 articles (45%)** appear in two or more languages' top 50
- **"Heart"** is the single most universal medical article, appearing in **174 out of 337** language editions' top 50
- Only **16 articles** appear in 100+ languages' top 50 — truly global medical interests
- **Pandemics & COVID** articles have the highest average language spread (75 languages per article)
- **European languages cluster tightly** in their reading patterns, while Persian and Japanese show more unique interests
- **Mental health and drug-related articles** are popular but concentrated in larger Wikipedias rather than spreading universally

## Visualizations

All charts are styled after *The Economist*.

### Top 30 most universal medical articles (by language count)
![Top 30 most universal articles](images/eco_fig1_universal_articles.png)

### Top 50 articles by total pageviews
![Top 25 by views](images/eco_fig20_top50_views.png)
![Ranks 26–50 by views](images/eco_fig21_top50_views.png)

### Overlap distribution
![Overlap distribution](images/eco_fig2_overlap_distribution.png)

### Cumulative universality curve
![Cumulative curve](images/eco_fig3_cumulative.png)

### Article × Language heatmap (top 20 × 20)
![Heatmap](images/eco_fig4_heatmap.png)

### Language pair overlap matrix
![Language pairs](images/eco_fig5_language_pairs.png)

### Thematic category breakdown
![Categories](images/eco_fig6_categories.png)

### Average language spread by category
![Category spread](images/eco_fig7_category_spread.png)

## Cluster Analysis

Using Jaccard similarity on each language's top-50 article set (unified via Wikidata), hierarchical clustering reveals **8 natural reading-pattern clusters** across 237 languages. Key findings:

- **Major European cluster** (35 languages): Germanic, Romance, and Slavic languages share strong overlap. Distinctive articles include mental health conditions (Asperger syndrome, borderline personality disorder), historical figures (Josef Mengele), and Western-centric topics (Lyme disease, lobotomy).
- **Middle Eastern & South Asian cluster** (22 languages): Hindi, Bengali, Tamil, Urdu, Swahili, and others. Distinctive articles reflect tropical/developing-world health concerns — dengue fever, typhoid, jaundice, hemorrhoids, and malnutrition.
- **Sub-Saharan African cluster** (7 languages): Xhosa, Igbo, Nyanja, etc. Uniquely focused on vaccines (pertussis, meningococcal, hepatitis A), neglected tropical diseases (leishmaniasis, schistosomiasis), and public health infrastructure (pit latrines).
- **Southeast Asian & Turkic cluster** (13 languages): Indonesian, Vietnamese, Thai, Kazakh, etc. Distinctive for practical medical topics — appendicitis, first aid, anemia, vitamin C.

### Dendrogram: Language similarity tree
![Dendrogram](images/eco_fig8_dendrogram.png)

### Cluster composition by language family
![Cluster composition](images/eco_fig9_cluster_composition.png)

### Distinctive articles per cluster
![Cluster signatures](images/eco_fig10_cluster_signatures.png)

### Inter-cluster similarity
![Cluster similarity](images/eco_fig11_cluster_similarity.png)

## Methodology

1. **Data collection**: Fetched the top 50 most-viewed medical articles for each of the 337 Wikipedia language editions from the [mdwiki Toolforge dashboard](https://mdwiki.toolforge.org/views/index.php?sub_dir=users-agents) (user/agent pageviews, 2016–2025).

2. **Wikidata unification**: Queried the [Wikidata API](https://www.wikidata.org/w/api.php) to map each local-language article title to its Wikidata QID, enabling cross-language comparison. Achieved a **97% match rate** across 12,037 article entries.

3. **Overlap analysis**: Built a unified article map (QID → languages) to identify which articles appear in multiple languages' top 50 lists, and calculated pairwise language overlap.

4. **Cluster analysis**: Computed Jaccard similarity between all language pairs based on their Wikidata-unified top-50 sets, then applied Ward hierarchical clustering (via scipy) to discover natural reading-pattern groups. Characterised each cluster by its "signature" articles (high lift vs. other clusters).

5. **Visualization**: Generated Economist-style charts using matplotlib and seaborn.

## Repository Structure

```
├── README.md
├── top50_medical_articles.html        # Interactive explorer — open in browser
├── code/
│   ├── 01_fetch_all_languages.py      # Fetch top-50 articles for all 337 languages
│   ├── 02_wikidata_unification.py     # Query Wikidata for cross-language mapping
│   ├── 03_analyze_overlap.py          # Overlap analysis + basic visualizations
│   ├── 04_economist_charts.py         # Economist-style chart generation
│   ├── 05_cluster_analysis.py         # Hierarchical clustering & cluster characterisation
│   ├── 06_fetch_timeseries.py         # Fetch year-by-year pageview data (2016–2025)
│   └── 07_trend_charts.py            # Time-trend visualisations (fig12–fig19)
├── data/
│   ├── all_languages_overlap_analysis.csv
│   ├── all_languages_summary.json
│   └── cluster_analysis.json
└── images/
    ├── eco_fig1–fig11                 # Cross-language overlap & cluster charts
    └── eco_fig12–fig19                # Time-trend charts (2016–2025)
```

## How to Reproduce

```bash
# Stage 1: Fetch data (takes ~10 min, makes ~337 API calls)
python3 code/01_fetch_all_languages.py

# Stage 2: Wikidata unification (takes ~15 min, makes ~337 API calls)
python3 code/02_wikidata_unification.py

# Stage 3: Analysis and basic charts
python3 code/03_analyze_overlap.py

# Stage 4: Economist-style charts
pip install matplotlib seaborn pandas scipy
python3 code/04_economist_charts.py

# Stage 5: Cluster analysis
python3 code/05_cluster_analysis.py
```

## Data Sources

- **Pageview data**: [WikiProject Medicine Dashboard](https://mdwiki.toolforge.org/views/index.php?sub_dir=users-agents) (mdwiki.toolforge.org)
- **Article unification**: [Wikidata API](https://www.wikidata.org/w/api.php) (`wbgetentities` with `sites` and `titles` parameters)

## License

Data sourced from Wikipedia/Wikidata (CC BY-SA 4.0). Code in this repository is MIT licensed.
