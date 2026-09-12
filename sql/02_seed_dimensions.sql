-- Lookup tables for the six GCC countries and a small indicator list.

INSERT INTO dim_country (country_id, iso3, country_name, region) VALUES
    (1, 'BHR', 'Bahrain',        'GCC'),
    (2, 'KWT', 'Kuwait',         'GCC'),
    (3, 'OMN', 'Oman',           'GCC'),
    (4, 'QAT', 'Qatar',          'GCC'),
    (5, 'SAU', 'Saudi Arabia',   'GCC'),
    (6, 'ARE', 'United Arab Emirates', 'GCC');

INSERT INTO dim_indicator (
    indicator_id,
    indicator_code,
    indicator_name,
    unit,
    category,
    source_name,
    source_indicator_code,
    source_url
) VALUES
    (1, 'POP_MN',        'Population',               'million people',     'Demography', 'World Bank WDI', 'SP.POP.TOTL',       'https://data.worldbank.org/indicator/SP.POP.TOTL'),
    (2, 'GDP_USD_BN',    'GDP (current)',            'billion US dollars', 'Economy',    'World Bank WDI', 'NY.GDP.MKTP.CD',     'https://data.worldbank.org/indicator/NY.GDP.MKTP.CD'),
    (3, 'GDP_PC_USD',    'GDP per capita',           'US dollars',         'Economy',    'World Bank WDI', 'NY.GDP.PCAP.CD',     'https://data.worldbank.org/indicator/NY.GDP.PCAP.CD'),
    (4, 'OIL_RENT_PCT',  'Oil rents',                'percent of GDP',     'Energy',     'World Bank WDI', 'NY.GDP.PETR.RT.ZS',  'https://data.worldbank.org/indicator/NY.GDP.PETR.RT.ZS'),
    (5, 'INFLATION_PCT', 'Consumer price inflation', 'percent',            'Prices',     'World Bank WDI', 'FP.CPI.TOTL.ZG',      'https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG'),
    (6, 'UNEMP_PCT',     'Unemployment rate',        'percent',            'Labor',      'World Bank WDI', 'SL.UEM.TOTL.ZS',      'https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS'),
    (7, 'LIFE_EXP',      'Life expectancy at birth', 'years',              'Health',     'World Bank WDI', 'SP.DYN.LE00.IN',      'https://data.worldbank.org/indicator/SP.DYN.LE00.IN'),
    (8, 'BIRTH_RATE',    'Crude birth rate',         'per 1,000 people',   'Demography', 'World Bank WDI', 'SP.DYN.CBRT.IN',     'https://data.worldbank.org/indicator/SP.DYN.CBRT.IN');

INSERT INTO dim_year (year) VALUES
    (2000), (2001), (2002), (2003), (2004), (2005), (2006),
    (2007), (2008), (2009), (2010), (2011), (2012), (2013),
    (2014), (2015), (2016), (2017), (2018), (2019), (2020),
    (2021), (2022), (2023), (2024), (2025), (2026);
