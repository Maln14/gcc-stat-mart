-- Practice queries. Run after 01-04.
-- Highlight a query and execute it (do not run this whole file at once
-- unless your tool shows multiple result sets).

-- 1) Beginner: list the countries
SELECT country_id, iso3, country_name
FROM dim_country
ORDER BY country_name;

-- 2) Beginner: one country, one indicator
SELECT year, value
FROM vw_gcc_indicators
WHERE country_name = 'Saudi Arabia'
  AND indicator_code = 'GDP_USD_BN'
ORDER BY year;

-- 3) Beginner: latest year in the mart
SELECT MAX(year) AS latest_year
FROM fact_indicator;

-- 4) Beginner: GDP in the latest year, largest first
SELECT
    country_name,
    value AS gdp_billion_usd
FROM vw_gcc_indicators
WHERE indicator_code = 'GDP_USD_BN'
  AND year = 2023
ORDER BY value DESC;

-- 5) Beginner: GROUP BY — average oil rents over the sample years
SELECT
    country_name,
    ROUND(AVG(value), 1) AS avg_oil_rent_pct
FROM vw_gcc_indicators
WHERE indicator_code = 'OIL_RENT_PCT'
GROUP BY country_name
ORDER BY avg_oil_rent_pct DESC;

-- 6) Intermediate: CASE — label how oil-dependent a country looks in 2023
SELECT
    country_name,
    value AS oil_rent_pct,
    CASE
        WHEN value >= 30 THEN 'High'
        WHEN value >= 15 THEN 'Medium'
        ELSE 'Lower'
    END AS oil_dependence
FROM vw_gcc_indicators
WHERE indicator_code = 'OIL_RENT_PCT'
  AND year = 2023
ORDER BY value DESC;

-- 7) Intermediate: compare 2019 vs 2020 GDP (COVID shock) with a self-join
SELECT
    this_year.country_name,
    prev.value AS gdp_2019,
    this_year.value AS gdp_2020,
    ROUND(this_year.value - prev.value, 1) AS change_bn,
    ROUND((this_year.value - prev.value) * 100.0 / prev.value, 1) AS pct_change
FROM vw_gcc_indicators AS this_year
JOIN vw_gcc_indicators AS prev
    ON this_year.iso3 = prev.iso3
   AND this_year.indicator_code = prev.indicator_code
   AND this_year.year = prev.year + 1
WHERE this_year.indicator_code = 'GDP_USD_BN'
  AND this_year.year = 2020
ORDER BY pct_change;

-- 8) Intermediate: year-over-year population change for every year
SELECT
    this_year.country_name,
    this_year.year,
    this_year.value AS pop_million,
    prev.value AS pop_previous_year,
    ROUND((this_year.value - prev.value) * 100.0 / prev.value, 1) AS yoy_pct
FROM vw_gcc_indicators AS this_year
JOIN vw_gcc_indicators AS prev
    ON this_year.iso3 = prev.iso3
   AND this_year.indicator_code = prev.indicator_code
   AND this_year.year = prev.year + 1
WHERE this_year.indicator_code = 'POP_MN'
ORDER BY this_year.country_name, this_year.year;

-- 9) Intermediate: LEFT JOIN data-quality check
-- Staging rows that did not land in the fact table (bad code or year)
SELECT
    s.iso3,
    s.indicator_code,
    s.year,
    s.value
FROM stg_indicator_raw AS s
LEFT JOIN dim_country AS c
    ON c.iso3 = s.iso3
LEFT JOIN dim_indicator AS i
    ON i.indicator_code = s.indicator_code
LEFT JOIN dim_year AS y
    ON y.year = s.year
WHERE c.country_id IS NULL
   OR i.indicator_id IS NULL
   OR y.year IS NULL;

-- 10) Counts should match if every staging row was valid
SELECT
    (SELECT COUNT(*) FROM stg_indicator_raw) AS staging_rows,
    (SELECT COUNT(*) FROM fact_indicator) AS fact_rows;
