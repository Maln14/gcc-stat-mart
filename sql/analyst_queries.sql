-- Latest GDP per capita ranking
SELECT country_name, year, value, rank_desc, gcc_average
FROM vw_latest_ranks
WHERE indicator_code = 'GDP_PC_USD'
ORDER BY rank_desc;

-- Oil dependence bands
SELECT
    country_name,
    year,
    value AS oil_rent_pct,
    CASE
        WHEN value >= 30 THEN 'High dependence'
        WHEN value >= 15 THEN 'Medium dependence'
        ELSE 'Lower dependence'
    END AS oil_dependence
FROM vw_latest_ranks
WHERE indicator_code = 'OIL_RENT_PCT'
ORDER BY value DESC;

-- Year-over-year GDP change
SELECT country_name, year, value, previous_value, yoy_pct
FROM vw_indicator_yoy
WHERE indicator_code = 'GDP_USD_BN'
  AND year = (
      SELECT MAX(year)
      FROM vw_indicator_yoy
      WHERE indicator_code = 'GDP_USD_BN'
  )
ORDER BY yoy_pct;

-- Staging rows that failed dimension joins
SELECT s.iso3, s.indicator_code, s.year, s.value
FROM stg_indicator_raw AS s
LEFT JOIN dim_country AS c ON c.iso3 = s.iso3
LEFT JOIN dim_indicator AS i ON i.indicator_code = s.indicator_code
LEFT JOIN dim_year AS y ON y.year = s.year
WHERE c.country_id IS NULL
   OR i.indicator_id IS NULL
   OR y.year IS NULL;
