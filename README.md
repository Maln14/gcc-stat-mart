# GCC statistical mart

A small **SQLite** project that stores comparable indicators for the GCC countries in a star schema:

- `dim_country`, `dim_indicator`, `dim_year` — lookup tables
- `stg_indicator_raw` — landing table 
- `fact_indicator` — clean table: **one row = one country + one indicator + one year**
- `vw_gcc_indicators` — day to day query



The dashboard uses official [World Bank World Development Indicators](https://data.worldbank.org/indicator)
downloaded through the World Bank API. Population is converted to millions and
GDP to billions of current US dollars; the other indicators retain their
published units. Latest available years differ by indicator.

**Live Dash dashboard:** <https://gcc-stat-mart-dash.onrender.com>

## Run the Dash dashboard

The primary presentation is a Plotly Dash app:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python dash_app.py
```

Then open <http://localhost:8050>.

## Refresh the official data

```powershell
.\.venv\Scripts\Activate.ps1
python scripts\fetch_world_bank.py
```

This downloads all eight indicators for the six GCC countries from 2000
through the current year and writes:

- `data/raw/gcc_indicators_world_bank.csv` — normalized observations
- `data/raw/world_bank_metadata.json` — retrieval time and coverage

Restart `dash_app.py` after refreshing. It rebuilds `gcc_stat.db` whenever the
CSV or schema scripts are newer than the database.

## SQL pipeline

1. `sql/01_create_tables.sql` creates dimensions, staging, and facts.
2. `sql/02_seed_dimensions.sql` inserts GCC countries, indicator definitions,
   World Bank source codes, and years.
3. Python imports the normalized World Bank CSV into `stg_indicator_raw`.
4. `sql/04_build_facts.sql` validates codes through joins and builds the fact
   table and analyst-friendly view.
5. `sql/05_queries.sql` contains the queries.

## Folder layout

```
assets/       Dash presentation styles
data/raw/     committed World Bank data and retrieval metadata
scripts/      reproducible World Bank API downloader
sql/          schema, dimensions, transformation, and practice queries
```

The original teaching CSV and `03_load_sample.sql` remain for learning, but the
Dash application does not use them.
