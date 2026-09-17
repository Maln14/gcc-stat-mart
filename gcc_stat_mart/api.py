"""JSON/CSV/XLSX API for mart views."""

from __future__ import annotations

import json
import sqlite3
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Blueprint, Response, jsonify, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "gcc_stat.db"
METADATA_FILE = ROOT / "data" / "raw" / "world_bank_metadata.json"

api_bp = Blueprint("api", __name__, url_prefix="/api")
_ACTIVE_DB = DEFAULT_DB


def _db_path() -> Path:
    return _ACTIVE_DB


def _query(sql: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with sqlite3.connect(_db_path()) as connection:
        return pd.read_sql_query(sql, connection, params=params)


def _parse_list(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return values or None


def _filter_frame(
    frame: pd.DataFrame,
    *,
    countries: list[str] | None = None,
    indicators: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> pd.DataFrame:
    filtered = frame
    if countries:
        country_col = "country_name" if "country_name" in filtered.columns else None
        if country_col:
            filtered = filtered[filtered[country_col].isin(countries)]
    if indicators and "indicator_code" in filtered.columns:
        filtered = filtered[filtered["indicator_code"].isin(indicators)]
    if year_from is not None and "year" in filtered.columns:
        filtered = filtered[filtered["year"] >= year_from]
    if year_to is not None and "year" in filtered.columns:
        filtered = filtered[filtered["year"] <= year_to]
    return filtered


def _request_filters() -> dict[str, Any]:
    year_from = request.args.get("year_from", type=int)
    year_to = request.args.get("year_to", type=int)
    return {
        "countries": _parse_list(request.args.get("countries")),
        "indicators": _parse_list(request.args.get("indicators")),
        "year_from": year_from,
        "year_to": year_to,
    }


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8")


def dataframe_to_xlsx_bytes(frame: pd.DataFrame, sheet_name: str = "data") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()


def load_indicator_export(
    *,
    countries: list[str] | None = None,
    indicators: list[str] | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> pd.DataFrame:
    frame = _query(
        """
        SELECT
            iso3,
            country_name,
            indicator_code,
            indicator_name,
            unit,
            category,
            year,
            value,
            source_indicator_code,
            source_url
        FROM vw_gcc_indicators
        ORDER BY category, indicator_code, country_name, year
        """
    )
    return _filter_frame(
        frame,
        countries=countries,
        indicators=indicators,
        year_from=year_from,
        year_to=year_to,
    ).reset_index(drop=True)


@api_bp.get("/health")
def health() -> Response:
    db_exists = _db_path().exists()
    payload = {
        "status": "ok" if db_exists else "degraded",
        "database": str(_db_path()),
        "database_exists": db_exists,
    }
    return jsonify(payload), (200 if db_exists else 503)


@api_bp.get("/meta")
def meta() -> Response:
    metadata = {}
    if METADATA_FILE.exists():
        metadata = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
    counts = _query(
        """
        SELECT
            (SELECT COUNT(*) FROM dim_country) AS countries,
            (SELECT COUNT(*) FROM dim_indicator) AS indicators,
            (SELECT COUNT(*) FROM fact_indicator) AS facts,
            (SELECT MIN(year) FROM fact_indicator) AS first_year,
            (SELECT MAX(year) FROM fact_indicator) AS last_year
        """
    ).iloc[0].to_dict()
    return jsonify({"world_bank": metadata, "mart": counts})


@api_bp.get("/countries")
def countries() -> Response:
    frame = _query(
        "SELECT iso3, country_name, region FROM dim_country ORDER BY country_name"
    )
    return jsonify(frame.to_dict(orient="records"))


@api_bp.get("/indicators")
def indicators() -> Response:
    frame = _query(
        """
        SELECT
            indicator_code,
            indicator_name,
            unit,
            category,
            source_indicator_code,
            source_url
        FROM dim_indicator
        ORDER BY category, indicator_name
        """
    )
    return jsonify(frame.to_dict(orient="records"))


@api_bp.get("/observations")
def observations() -> Response:
    filters = _request_filters()
    frame = load_indicator_export(**filters)
    return jsonify(
        {
            "count": int(len(frame)),
            "filters": filters,
            "data": frame.to_dict(orient="records"),
        }
    )


@api_bp.get("/ranks")
def ranks() -> Response:
    filters = _request_filters()
    frame = _query(
        """
        SELECT
            iso3,
            country_name,
            indicator_code,
            indicator_name,
            unit,
            category,
            year,
            value,
            rank_desc,
            rank_asc,
            gcc_average
        FROM vw_latest_ranks
        ORDER BY category, indicator_code, rank_desc
        """
    )
    frame = _filter_frame(
        frame,
        countries=filters["countries"],
        indicators=filters["indicators"],
    ).reset_index(drop=True)
    return jsonify({"count": int(len(frame)), "data": frame.to_dict(orient="records")})


@api_bp.get("/yoy")
def yoy() -> Response:
    filters = _request_filters()
    frame = _query(
        """
        SELECT
            iso3,
            country_name,
            indicator_code,
            indicator_name,
            unit,
            category,
            year,
            value,
            previous_value,
            yoy_pct
        FROM vw_indicator_yoy
        ORDER BY indicator_code, country_name, year
        """
    )
    frame = _filter_frame(
        frame,
        countries=filters["countries"],
        indicators=filters["indicators"],
        year_from=filters["year_from"],
        year_to=filters["year_to"],
    ).reset_index(drop=True)
    return jsonify({"count": int(len(frame)), "data": frame.to_dict(orient="records")})


@api_bp.get("/export.csv")
def export_csv() -> Response:
    filters = _request_filters()
    frame = load_indicator_export(**filters)
    return Response(
        dataframe_to_csv_bytes(frame),
        mimetype="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=gcc_stat_mart_export.csv"
        },
    )


@api_bp.get("/export.xlsx")
def export_xlsx() -> Response:
    filters = _request_filters()
    frame = load_indicator_export(**filters)
    return Response(
        dataframe_to_xlsx_bytes(frame, sheet_name="observations"),
        mimetype=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": "attachment; filename=gcc_stat_mart_export.xlsx"
        },
    )


def register_api(app, *, database: Path | None = None) -> None:
    global _ACTIVE_DB
    _ACTIVE_DB = Path(database) if database else DEFAULT_DB
    if "api" not in app.blueprints:
        app.register_blueprint(api_bp)
