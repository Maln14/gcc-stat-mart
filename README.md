# GCC Statistical Mart

World Bank indicators for the six GCC countries in a SQLite star schema, with a Dash dashboard for peer comparison.

**Live:** https://gcc-stat-mart-dash.onrender.com

## Schema

| Name | Role |
| --- | --- |
| `dim_country` | countries |
| `dim_indicator` | indicators |
| `dim_year` | years |
| `stg_indicator_raw` | staging / landing |
| `fact_indicator` | facts (country + indicator + year) |
| `vw_gcc_indicators` | joined view |
| `vw_indicator_yoy` | year-over-year change |
| `vw_latest_ranks` | latest-year ranks |

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_mart.py
python dash_app.py
```

Open http://127.0.0.1:8765

Refresh data: `python scripts/fetch_world_bank.py && python scripts/build_mart.py`
