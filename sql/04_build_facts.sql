-- Move staging rows into the clean fact table.
-- We join on codes so country names and units live in dimension tables only.

DROP VIEW IF EXISTS vw_gcc_indicators;

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

-- Friendly view: analysts query this instead of remembering IDs.
CREATE VIEW vw_gcc_indicators AS
SELECT
    c.iso3,
    c.country_name,
    i.indicator_code,
    i.indicator_name,
    i.unit,
    i.category,
    f.year,
    f.value
FROM fact_indicator AS f
JOIN dim_country AS c
    ON c.country_id = f.country_id
JOIN dim_indicator AS i
    ON i.indicator_id = f.indicator_id;
