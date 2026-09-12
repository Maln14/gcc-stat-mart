# GCC statistical mart

A small **SQLite** project that stores comparable indicators for the six GCC countries in a star schema:

- `dim_country`, `dim_indicator`, `dim_year` — lookup tables
- `stg_indicator_raw` — landing table (one messy CSV-style table)
- `fact_indicator` — clean table: **one row = one country + one indicator + one year**
- `vw_gcc_indicators` — the view you should query day to day

SQL stays at **beginner to intermediate**: `SELECT`, `WHERE`, `JOIN`, `GROUP BY`, `CASE`, and one **self-join** for year-over-year change. No window functions.

Sample numbers in `data/raw/` are **illustrative** (rounded, teaching-scale). Swap them later for [GCC-Stat](https://dp.marsa.gccstat.org/) or World Bank CSVs.

## Run the Dash dashboard

The primary presentation is a Plotly Dash app:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python dash_app.py
```

Then open <http://localhost:8050>.

## How to run

1. Install [DB Browser for SQLite](https://sqlitebrowser.org/) (or any SQLite client).
2. Create a new database file in this folder named `gcc_stat.db`.
3. Open and run, in order:
   - `sql/01_create_tables.sql`
   - `sql/02_seed_dimensions.sql`
   - `sql/03_load_sample.sql`
   - `sql/04_build_facts.sql`
4. Run queries one at a time from `sql/05_queries.sql`.

If you use the `sqlite3` CLI from this folder:

```bash
sqlite3 gcc_stat.db ".read sql/01_create_tables.sql"
sqlite3 gcc_stat.db ".read sql/02_seed_dimensions.sql"
sqlite3 gcc_stat.db ".read sql/03_load_sample.sql"
sqlite3 gcc_stat.db ".read sql/04_build_facts.sql"
```

## Folder layout

```
data/raw/     sample CSV (same numbers as 03_load_sample.sql)
sql/          scripts in run order
```

## Next steps (when you want official data)

1. Download a GCC-Stat or World Bank CSV.
2. Map columns to `iso3`, `indicator_code`, `year`, `value`.
3. Add any new codes to `dim_indicator`.
4. Reload staging, then run `04_build_facts.sql` again.
