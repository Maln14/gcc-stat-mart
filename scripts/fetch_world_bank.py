"""Download comparable GCC indicators from the World Bank WDI API."""

from argparse import ArgumentParser
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import requests

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    # Most systems already have a usable Python certificate store.
    pass


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "raw" / "gcc_indicators_world_bank.csv"
METADATA_OUTPUT = ROOT / "data" / "raw" / "world_bank_metadata.json"
API_ROOT = "https://api.worldbank.org/v2"
COUNTRIES = ["BHR", "KWT", "OMN", "QAT", "SAU", "ARE"]

# Internal mart code: (World Bank indicator code, unit divisor)
INDICATORS = {
    "POP_MN": ("SP.POP.TOTL", 1_000_000),
    "GDP_USD_BN": ("NY.GDP.MKTP.CD", 1_000_000_000),
    "GDP_PC_USD": ("NY.GDP.PCAP.CD", 1),
    "OIL_RENT_PCT": ("NY.GDP.PETR.RT.ZS", 1),
    "INFLATION_PCT": ("FP.CPI.TOTL.ZG", 1),
    "UNEMP_PCT": ("SL.UEM.TOTL.ZS", 1),
    "LIFE_EXP": ("SP.DYN.LE00.IN", 1),
    "BIRTH_RATE": ("SP.DYN.CBRT.IN", 1),
}


def fetch_indicator(
    internal_code: str,
    world_bank_code: str,
    divisor: int,
    start_year: int,
    end_year: int,
) -> list[dict]:
    country_path = ";".join(COUNTRIES)
    url = f"{API_ROOT}/country/{country_path}/indicator/{world_bank_code}"
    response = requests.get(
        url,
        params={
            "format": "json",
            "per_page": 20_000,
            "date": f"{start_year}:{end_year}",
        },
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, list) or len(payload) < 2 or payload[1] is None:
        raise RuntimeError(f"No World Bank data returned for {world_bank_code}")

    rows = []
    for observation in payload[1]:
        value = observation["value"]
        iso3 = observation["countryiso3code"]
        if value is None or iso3 not in COUNTRIES:
            continue

        rows.append(
            {
                "iso3": iso3,
                "indicator_code": internal_code,
                "year": int(observation["date"]),
                "value": float(value) / divisor,
                "notes": f"World Bank WDI indicator {world_bank_code}",
            }
        )
    return rows


def main() -> None:
    current_year = datetime.now(timezone.utc).year
    parser = ArgumentParser()
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=current_year)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    all_rows = []
    coverage = {}
    for internal_code, (world_bank_code, divisor) in INDICATORS.items():
        rows = fetch_indicator(
            internal_code,
            world_bank_code,
            divisor,
            args.start_year,
            args.end_year,
        )
        all_rows.extend(rows)
        coverage[internal_code] = {
            "world_bank_indicator": world_bank_code,
            "rows": len(rows),
            "first_year": min(row["year"] for row in rows),
            "last_year": max(row["year"] for row in rows),
        }
        print(
            f"{internal_code}: {len(rows)} rows "
            f"({coverage[internal_code]['first_year']}-"
            f"{coverage[internal_code]['last_year']})"
        )

    all_rows.sort(
        key=lambda row: (
            row["indicator_code"],
            row["iso3"],
            row["year"],
        )
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["iso3", "indicator_code", "year", "value", "notes"],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    metadata = {
        "source": "World Bank World Development Indicators",
        "api": API_ROOT,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_years": [args.start_year, args.end_year],
        "rows": len(all_rows),
        "coverage": coverage,
    }
    METADATA_OUTPUT.write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(all_rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
