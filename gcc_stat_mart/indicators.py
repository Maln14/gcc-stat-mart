"""Single source of truth for GCC mart indicators and countries."""

from __future__ import annotations

COUNTRIES = [
    {"iso3": "BHR", "country_name": "Bahrain", "region": "GCC"},
    {"iso3": "KWT", "country_name": "Kuwait", "region": "GCC"},
    {"iso3": "OMN", "country_name": "Oman", "region": "GCC"},
    {"iso3": "QAT", "country_name": "Qatar", "region": "GCC"},
    {"iso3": "SAU", "country_name": "Saudi Arabia", "region": "GCC"},
    {"iso3": "ARE", "country_name": "United Arab Emirates", "region": "GCC"},
]

COUNTRY_COLORS = {
    "Bahrain": "#1d4ed8",
    "Kuwait": "#b45309",
    "Oman": "#b91c1c",
    "Qatar": "#6d28d9",
    "Saudi Arabia": "#15803d",
    "United Arab Emirates": "#0e7490",
}

# Internal code -> World Bank mapping and display metadata.
INDICATORS = {
    "POP_MN": {
        "world_bank_code": "SP.POP.TOTL",
        "divisor": 1_000_000,
        "indicator_name": "Population",
        "unit": "million people",
        "category": "Demography",
        "source_url": "https://data.worldbank.org/indicator/SP.POP.TOTL",
        "chart": "trend",
        "format": ",.1f",
        "higher_is_better": None,
    },
    "GDP_USD_BN": {
        "world_bank_code": "NY.GDP.MKTP.CD",
        "divisor": 1_000_000_000,
        "indicator_name": "GDP (current)",
        "unit": "billion US dollars",
        "category": "Economy",
        "source_url": "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        "chart": "trend",
        "format": ",.1f",
        "higher_is_better": True,
    },
    "GDP_PC_USD": {
        "world_bank_code": "NY.GDP.PCAP.CD",
        "divisor": 1,
        "indicator_name": "GDP per capita",
        "unit": "US dollars",
        "category": "Economy",
        "source_url": "https://data.worldbank.org/indicator/NY.GDP.PCAP.CD",
        "chart": "rank",
        "format": ",.0f",
        "higher_is_better": True,
    },
    "OIL_RENT_PCT": {
        "world_bank_code": "NY.GDP.PETR.RT.ZS",
        "divisor": 1,
        "indicator_name": "Oil rents",
        "unit": "percent of GDP",
        "category": "Energy",
        "source_url": "https://data.worldbank.org/indicator/NY.GDP.PETR.RT.ZS",
        "chart": "rank",
        "format": ",.1f",
        "higher_is_better": False,
        "thresholds": [
            {"min": 30, "label": "High dependence", "tone": "warn"},
            {"min": 15, "label": "Medium dependence", "tone": "mid"},
            {"min": None, "label": "Lower dependence", "tone": "ok"},
        ],
    },
    "INFLATION_PCT": {
        "world_bank_code": "FP.CPI.TOTL.ZG",
        "divisor": 1,
        "indicator_name": "Consumer price inflation",
        "unit": "percent",
        "category": "Prices",
        "source_url": "https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG",
        "chart": "small_multiples_bar",
        "format": ",.1f",
        "higher_is_better": False,
    },
    "UNEMP_PCT": {
        "world_bank_code": "SL.UEM.TOTL.ZS",
        "divisor": 1,
        "indicator_name": "Unemployment rate",
        "unit": "percent",
        "category": "Labor",
        "source_url": "https://data.worldbank.org/indicator/SL.UEM.TOTL.ZS",
        "chart": "dumbbell",
        "format": ",.1f",
        "higher_is_better": False,
    },
    "LIFE_EXP": {
        "world_bank_code": "SP.DYN.LE00.IN",
        "divisor": 1,
        "indicator_name": "Life expectancy at birth",
        "unit": "years",
        "category": "Health",
        "source_url": "https://data.worldbank.org/indicator/SP.DYN.LE00.IN",
        "chart": "compare_endpoints",
        "format": ",.1f",
        "higher_is_better": True,
    },
    "BIRTH_RATE": {
        "world_bank_code": "SP.DYN.CBRT.IN",
        "divisor": 1,
        "indicator_name": "Crude birth rate",
        "unit": "per 1,000 people",
        "category": "Demography",
        "source_url": "https://data.worldbank.org/indicator/SP.DYN.CBRT.IN",
        "chart": "small_multiples_line",
        "format": ",.1f",
        "higher_is_better": None,
    },
}


def oil_dependence_label(value: float) -> str:
    if value >= 30:
        return "High dependence"
    if value >= 15:
        return "Medium dependence"
    return "Lower dependence"
