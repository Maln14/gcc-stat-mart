"""Build the SQLite mart from World Bank CSV."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import pandas as pd

from gcc_stat_mart.indicators import COUNTRIES, INDICATORS

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "gcc_stat.db"
DEFAULT_CSV = ROOT / "data" / "raw" / "gcc_indicators_world_bank.csv"


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS dim_country (
    country_id   INTEGER PRIMARY KEY,
    iso3         TEXT NOT NULL UNIQUE,
    country_name TEXT NOT NULL,
    region       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_indicator (
    indicator_id          INTEGER PRIMARY KEY,
    indicator_code        TEXT NOT NULL UNIQUE,
    indicator_name        TEXT NOT NULL,
    unit                  TEXT NOT NULL,
    category              TEXT NOT NULL,
    source_name           TEXT NOT NULL,
    source_indicator_code TEXT NOT NULL,
    source_url            TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_year (
    year INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS stg_indicator_raw (
    iso3           TEXT,
    indicator_code TEXT,
    year           INTEGER,
    value          REAL,
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS fact_indicator (
    country_id   INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL,
    year         INTEGER NOT NULL,
    value        REAL,
    PRIMARY KEY (country_id, indicator_id, year),
    FOREIGN KEY (country_id)   REFERENCES dim_country (country_id),
    FOREIGN KEY (indicator_id) REFERENCES dim_indicator (indicator_id),
    FOREIGN KEY (year)         REFERENCES dim_year (year)
);

CREATE TABLE IF NOT EXISTS mart_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)


def seed_dimensions(connection: sqlite3.Connection, years: list[int]) -> None:
    connection.execute("DELETE FROM fact_indicator")
    connection.execute("DELETE FROM stg_indicator_raw")
    connection.execute("DELETE FROM dim_country")
    connection.executemany(
        """
        INSERT INTO dim_country (country_id, iso3, country_name, region)
        VALUES (?, ?, ?, ?)
        """,
        [
            (index, row["iso3"], row["country_name"], row["region"])
            for index, row in enumerate(COUNTRIES, start=1)
        ],
    )

    connection.execute("DELETE FROM dim_indicator")
    connection.executemany(
        """
        INSERT INTO dim_indicator (
            indicator_id, indicator_code, indicator_name, unit, category,
            source_name, source_indicator_code, source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                index,
                code,
                meta["indicator_name"],
                meta["unit"],
                meta["category"],
                "World Bank WDI",
                meta["world_bank_code"],
                meta["source_url"],
            )
            for index, (code, meta) in enumerate(INDICATORS.items(), start=1)
        ],
    )

    connection.execute("DELETE FROM dim_year")
    connection.executemany(
        "INSERT INTO dim_year (year) VALUES (?)",
        [(year,) for year in years],
    )


def load_staging(connection: sqlite3.Connection, csv_path: Path) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    required = {"iso3", "indicator_code", "year", "value"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    connection.execute("DELETE FROM stg_indicator_raw")
    frame.to_sql("stg_indicator_raw", connection, if_exists="append", index=False)
    return frame


def build_facts(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP VIEW IF EXISTS vw_gcc_indicators;
        DROP VIEW IF EXISTS vw_indicator_yoy;
        DROP VIEW IF EXISTS vw_latest_ranks;

        DELETE FROM fact_indicator;

        INSERT INTO fact_indicator (country_id, indicator_id, year, value)
        SELECT
            c.country_id,
            i.indicator_id,
            s.year,
            s.value
        FROM stg_indicator_raw AS s
        JOIN dim_country AS c
            ON c.iso3 = s.iso3
        JOIN dim_indicator AS i
            ON i.indicator_code = s.indicator_code
        JOIN dim_year AS y
            ON y.year = s.year
        WHERE s.value IS NOT NULL;

        CREATE VIEW vw_gcc_indicators AS
        SELECT
            c.iso3,
            c.country_name,
            i.indicator_code,
            i.indicator_name,
            i.unit,
            i.category,
            i.source_name,
            i.source_indicator_code,
            i.source_url,
            f.year,
            f.value
        FROM fact_indicator AS f
        JOIN dim_country AS c
            ON c.country_id = f.country_id
        JOIN dim_indicator AS i
            ON i.indicator_id = f.indicator_id;

        CREATE VIEW vw_indicator_yoy AS
        SELECT
            this_year.iso3,
            this_year.country_name,
            this_year.indicator_code,
            this_year.indicator_name,
            this_year.unit,
            this_year.category,
            this_year.year,
            this_year.value,
            prev.value AS previous_value,
            CASE
                WHEN prev.value IS NULL OR prev.value = 0 THEN NULL
                ELSE ROUND(
                    (this_year.value - prev.value) * 100.0 / prev.value,
                    2
                )
            END AS yoy_pct
        FROM vw_gcc_indicators AS this_year
        LEFT JOIN vw_gcc_indicators AS prev
            ON this_year.iso3 = prev.iso3
           AND this_year.indicator_code = prev.indicator_code
           AND this_year.year = prev.year + 1;

        CREATE VIEW vw_latest_ranks AS
        WITH latest AS (
            SELECT
                indicator_code,
                MAX(year) AS latest_year
            FROM vw_gcc_indicators
            GROUP BY indicator_code
        )
        SELECT
            v.iso3,
            v.country_name,
            v.indicator_code,
            v.indicator_name,
            v.unit,
            v.category,
            v.year,
            v.value,
            RANK() OVER (
                PARTITION BY v.indicator_code
                ORDER BY v.value DESC
            ) AS rank_desc,
            RANK() OVER (
                PARTITION BY v.indicator_code
                ORDER BY v.value ASC
            ) AS rank_asc,
            AVG(v.value) OVER (
                PARTITION BY v.indicator_code
            ) AS gcc_average
        FROM vw_gcc_indicators AS v
        JOIN latest AS l
            ON l.indicator_code = v.indicator_code
           AND l.latest_year = v.year;
        """
    )


def set_meta(connection: sqlite3.Connection, csv_path: Path) -> None:
    connection.execute("DELETE FROM mart_meta")
    connection.executemany(
        "INSERT INTO mart_meta (key, value) VALUES (?, ?)",
        [
            ("source_csv", str(csv_path)),
            ("built_by", "gcc_stat_mart.build"),
        ],
    )


def build_mart(db_path: Path, csv_path: Path) -> dict:
    if not csv_path.exists():
        raise FileNotFoundError(
            f"Missing {csv_path}. Run scripts/fetch_world_bank.py first."
        )

    frame = pd.read_csv(csv_path)
    years = sorted(frame["year"].dropna().astype(int).unique().tolist())
    if not years:
        raise RuntimeError("No years found in source CSV")

    years = list(range(min(years), max(years) + 2))

    with connect(db_path) as connection:
        ensure_schema(connection)
        seed_dimensions(connection, years)
        load_staging(connection, csv_path)
        build_facts(connection)
        set_meta(connection, csv_path)
        connection.commit()

        orphan_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM stg_indicator_raw AS s
            LEFT JOIN dim_country AS c ON c.iso3 = s.iso3
            LEFT JOIN dim_indicator AS i ON i.indicator_code = s.indicator_code
            LEFT JOIN dim_year AS y ON y.year = s.year
            WHERE c.country_id IS NULL
               OR i.indicator_id IS NULL
               OR y.year IS NULL
            """
        ).fetchone()[0]
        fact_count = connection.execute(
            "SELECT COUNT(*) FROM fact_indicator"
        ).fetchone()[0]
        staging_count = connection.execute(
            "SELECT COUNT(*) FROM stg_indicator_raw"
        ).fetchone()[0]

    return {
        "database": str(db_path),
        "staging_rows": staging_count,
        "fact_rows": fact_count,
        "orphan_rows": orphan_count,
        "year_span": [min(years), max(years)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    summary = build_mart(args.database, args.csv)
    print(
        f"Built {summary['database']}: "
        f"{summary['fact_rows']} fact rows "
        f"({summary['staging_rows']} staging, "
        f"{summary['orphan_rows']} orphans), "
        f"years {summary['year_span'][0]}-{summary['year_span'][1]}"
    )


if __name__ == "__main__":
    main()
