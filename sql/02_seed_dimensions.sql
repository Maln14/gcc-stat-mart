-- Lookup tables for the six GCC countries and a small indicator list.

INSERT INTO dim_country (country_id, iso3, country_name, region) VALUES
    (1, 'BHR', 'Bahrain',        'GCC'),
    (2, 'KWT', 'Kuwait',         'GCC'),
    (3, 'OMN', 'Oman',           'GCC'),
    (4, 'QAT', 'Qatar',          'GCC'),
    (5, 'SAU', 'Saudi Arabia',   'GCC'),
    (6, 'ARE', 'United Arab Emirates', 'GCC');

INSERT INTO dim_indicator (indicator_id, indicator_code, indicator_name, unit, category) VALUES
    (1, 'POP_MN',        'Population',                 'million people',     'Demography'),
    (2, 'GDP_USD_BN',    'GDP (current)',              'billion US dollars', 'Economy'),
    (3, 'GDP_PC_USD',    'GDP per capita',             'US dollars',         'Economy'),
    (4, 'OIL_RENT_PCT',  'Oil rents',                  'percent of GDP',     'Energy'),
    (5, 'INFLATION_PCT', 'Consumer price inflation',   'percent',            'Prices'),
    (6, 'UNEMP_PCT',     'Unemployment rate',          'percent',            'Labor'),
    (7, 'LIFE_EXP',      'Life expectancy at birth',   'years',              'Health'),
    (8, 'BIRTH_RATE',    'Crude birth rate',           'per 1,000 people',   'Demography');

INSERT INTO dim_year (year) VALUES
    (2018), (2019), (2020), (2021), (2022), (2023);
