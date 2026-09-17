# GCC Statistical Mart

SQLite statistical mart and Plotly Dash dashboard for comparable World Bank
indicators across the six GCC countries. The app focuses on peer benchmarking:
rankings, year-over-year change, and oil-dependence thresholds.

**Live dashboard:** <https://gcc-stat-mart-dash.onrender.com>

## Features

- Star-schema mart (`dim_*`, staging, `fact_indicator`) with analyst views
- Shared indicator config used by fetch, ETL, and the dashboard
- YoY change and latest-year rank views
- CSV / Excel export of the current selection
- JSON API over mart views (`/api/...`)
- Monthly World Bank refresh via GitHub Actions

## Schema

| Object | Role |
| --- | --- |
| `dim_country`, `dim_indicator`, `dim_year` | dimensions |
| `stg_indicator_raw` | landing table from World Bank CSV |
| `fact_indicator` | grain = country + indicator + year |
| `vw_gcc_indicators` | analyst-friendly wide view |
| `vw_indicator_yoy` | year-over-year percent change |
| `vw_latest_ranks` | latest-year ranks and GCC averages |

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_mart.py
python dash_app.py
```

Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

## API

| Endpoint | Description |
| --- | --- |
| `GET /api/health` | Process + database readiness |
| `GET /api/meta` | Retrieval metadata and mart counts |
| `GET /api/countries` | Country dimension |
| `GET /api/indicators` | Indicator dimension |
| `GET /api/observations` | Fact rows (`countries`, `indicators`, `year_from`, `year_to`) |
| `GET /api/ranks` | Latest-year ranks + GCC averages |
| `GET /api/yoy` | Year-over-year percent change |
| `GET /api/export.csv` | CSV download of observations |
| `GET /api/export.xlsx` | Excel download of observations |

Example:

```bash
curl "http://127.0.0.1:8765/api/observations?countries=Qatar,Bahrain&indicators=GDP_PC_USD&year_from=2015"
```

## Refresh official data

Manual:

```bash
python scripts/fetch_world_bank.py
python scripts/build_mart.py
```

Scheduled: `.github/workflows/refresh-world-bank.yml` runs monthly (and on
`workflow_dispatch`), refreshes the committed World Bank extract, rebuilds the
mart, and commits when the CSV changes.

Restart the Dash app after a refresh so it reloads in-memory frames. The
database rebuilds automatically when the CSV or mart builder is newer than
`gcc_stat.db`.

## Deploy

`render.yaml` defines a Render web service (`gcc-stat-mart-dash`).

Live URL: <https://gcc-stat-mart-dash.onrender.com>

After pushing to GitHub, trigger a manual deploy in the Render dashboard (or
enable auto-deploy from `main`) so the service picks up the latest commit.
Free-tier instances may sleep when idle and take a short time to wake.

## Folder layout

```
.github/workflows/  scheduled World Bank refresh
assets/             Dash styles
data/raw/           committed World Bank extract + retrieval metadata
gcc_stat_mart/      indicator config, mart builder, API
scripts/            fetch + build CLIs
dash_app.py         benchmarking dashboard + export buttons
```
