-- GCC statistical mart (beginner schema)
-- Run this first. SQLite is the default.

PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_gcc_indicators;
DROP TABLE IF EXISTS fact_indicator;
DROP TABLE IF EXISTS stg_indicator_raw;
DROP TABLE IF EXISTS dim_year;
DROP TABLE IF EXISTS dim_indicator;
DROP TABLE IF EXISTS dim_country;

CREATE TABLE dim_country (
    country_id   INTEGER PRIMARY KEY,
    iso3         TEXT NOT NULL UNIQUE,
    country_name TEXT NOT NULL,
    region       TEXT NOT NULL
);

CREATE TABLE dim_indicator (
    indicator_id         INTEGER PRIMARY KEY,
    indicator_code       TEXT NOT NULL UNIQUE,
    indicator_name       TEXT NOT NULL,
    unit                 TEXT NOT NULL,
    category             TEXT NOT NULL,
    source_name          TEXT NOT NULL,
    source_indicator_code TEXT NOT NULL,
    source_url           TEXT NOT NULL
);

CREATE TABLE dim_year (
    year INTEGER PRIMARY KEY
);

-- Messy landing table: one row per country / indicator / year
CREATE TABLE stg_indicator_raw (
    iso3           TEXT,
    indicator_code TEXT,
    year           INTEGER,
    value          REAL,
    notes          TEXT
);

-- Clean fact table: one grain = country + indicator + year
CREATE TABLE fact_indicator (
    country_id   INTEGER NOT NULL,
    indicator_id INTEGER NOT NULL,
    year         INTEGER NOT NULL,
    value        REAL,
    PRIMARY KEY (country_id, indicator_id, year),
    FOREIGN KEY (country_id)   REFERENCES dim_country (country_id),
    FOREIGN KEY (indicator_id) REFERENCES dim_indicator (indicator_id),
    FOREIGN KEY (year)         REFERENCES dim_year (year)
);
