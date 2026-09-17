"""GCC Statistical Mart — peer benchmarking dashboard."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, ctx, dcc, html
from plotly.subplots import make_subplots

from gcc_stat_mart.api import (
    dataframe_to_csv_bytes,
    dataframe_to_xlsx_bytes,
    load_indicator_export,
    register_api,
)
from gcc_stat_mart.build import DEFAULT_CSV, DEFAULT_DB, build_mart
from gcc_stat_mart.indicators import COUNTRY_COLORS, INDICATORS, oil_dependence_label

ROOT = Path(__file__).parent
DATABASE = DEFAULT_DB
METADATA_FILE = ROOT / "data" / "raw" / "world_bank_metadata.json"
PORT = 8765


def ensure_database() -> None:
    source_mtime = max(
        DEFAULT_CSV.stat().st_mtime,
        (ROOT / "gcc_stat_mart" / "indicators.py").stat().st_mtime,
        (ROOT / "gcc_stat_mart" / "build.py").stat().st_mtime,
    )
    if DATABASE.exists() and DATABASE.stat().st_mtime >= source_mtime:
        return
    build_mart(DATABASE, DEFAULT_CSV)


def run_query(query: str) -> pd.DataFrame:
    with sqlite3.connect(DATABASE) as connection:
        return pd.read_sql_query(query, connection)


ensure_database()
METADATA = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
RETRIEVED_DATE = METADATA["retrieved_at_utc"][:10]
COVERAGE = METADATA.get("coverage", {})

INDICATOR_FRAME = run_query(
    """
    SELECT indicator_code, indicator_name, unit, category
    FROM dim_indicator
    ORDER BY category, indicator_name
    """
)
COUNTRIES = run_query(
    "SELECT country_name FROM dim_country ORDER BY country_name"
)["country_name"].tolist()
ALL_DATA = run_query(
    """
    SELECT
        country_name,
        indicator_code,
        indicator_name,
        unit,
        category,
        year,
        value
    FROM vw_gcc_indicators
    ORDER BY category, indicator_name, country_name, year
    """
)
YOY_DATA = run_query(
    """
    SELECT country_name, indicator_code, year, value, previous_value, yoy_pct
    FROM vw_indicator_yoy
    """
)
RANK_DATA = run_query(
    """
    SELECT
        country_name,
        indicator_code,
        year,
        value,
        rank_desc,
        rank_asc,
        gcc_average
    FROM vw_latest_ranks
    """
)

FIRST_YEAR = int(ALL_DATA["year"].min())
LAST_YEAR = int(ALL_DATA["year"].max())
YEAR_SELECTIONS = {
    "range_full": (FIRST_YEAR, LAST_YEAR),
    "range_latest_5": (max(FIRST_YEAR, LAST_YEAR - 4), LAST_YEAR),
    "range_latest_10": (max(FIRST_YEAR, LAST_YEAR - 9), LAST_YEAR),
    "range_since_2010": (max(FIRST_YEAR, 2010), LAST_YEAR),
}
YEAR_SELECTIONS.update(
    {f"year_{year}": (year, year) for year in range(LAST_YEAR, FIRST_YEAR - 1, -1)}
)
YEAR_OPTIONS = [
    {
        "label": f"Full history ({FIRST_YEAR}–{LAST_YEAR})",
        "value": "range_full",
    },
    {
        "label": f"Latest 5 years ({LAST_YEAR - 4}–{LAST_YEAR})",
        "value": "range_latest_5",
    },
    {
        "label": f"Latest 10 years ({LAST_YEAR - 9}–{LAST_YEAR})",
        "value": "range_latest_10",
    },
    {
        "label": f"Since 2010 (2010–{LAST_YEAR})",
        "value": "range_since_2010",
    },
    *[
        {"label": str(year), "value": f"year_{year}"}
        for year in range(LAST_YEAR, FIRST_YEAR - 1, -1)
    ],
]


def style_figure(
    figure: go.Figure,
    unit: str | None = None,
    *,
    title: str | None = None,
) -> go.Figure:
    top_margin = 64 if title else 28
    figure.update_layout(
        height=320,
        margin={"l": 16, "r": 16, "t": top_margin, "b": 40},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "IBM Plex Sans, sans-serif", "color": "#1c2434", "size": 12},
        hoverlabel={"bgcolor": "#142033", "font_color": "white"},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.08 if title else 1.02,
            "xanchor": "right" if title else "left",
            "x": 1 if title else 0,
        },
        title=(
            {
                "text": title,
                "x": 0,
                "xanchor": "left",
                "y": 0.98,
                "yanchor": "top",
                "font": {"size": 13, "color": "#5b6b7c"},
            }
            if title
            else None
        ),
        xaxis={"gridcolor": "#e7edf5", "zerolinecolor": "#9aa8bc"},
        yaxis={"gridcolor": "#e7edf5", "title": None},
    )
    if unit:
        figure.update_xaxes(title=unit)
    return figure


def make_no_data_figure(label: str) -> go.Figure:
    figure = go.Figure()
    figure.add_annotation(
        text=f"No published values for {label}",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font={"size": 15, "color": "#64748b"},
    )
    figure.update_xaxes(visible=False)
    figure.update_yaxes(visible=False)
    return style_figure(figure)


def year_axis_settings(data: pd.DataFrame) -> dict:
    first_year = int(data["year"].min())
    span = int(data["year"].max()) - first_year
    if span <= 5:
        spacing = 1
    elif span <= 10:
        spacing = 2
    elif span <= 16:
        spacing = 3
    else:
        spacing = 5
    return {
        "title": None,
        "tickmode": "linear",
        "tick0": first_year,
        "dtick": spacing,
        "tickformat": "d",
        "automargin": True,
    }


def make_trend(data: pd.DataFrame, unit: str) -> go.Figure:
    figure = px.line(
        data.sort_values("year"),
        x="year",
        y="value",
        color="country_name",
        markers=True,
        color_discrete_map=COUNTRY_COLORS,
    )
    figure.update_traces(
        hovertemplate="%{fullData.name}<br>%{x}: %{y:,.2f}<extra></extra>"
    )
    figure.update_xaxes(**year_axis_settings(data))
    figure.update_yaxes(title=unit)
    return style_figure(figure)


def make_rank_bar(data: pd.DataFrame, unit: str, fmt: str) -> go.Figure:
    latest_year = int(data["year"].max())
    latest = data[data["year"] == latest_year].sort_values("value")
    average = latest["value"].mean()
    figure = px.bar(
        latest,
        x="value",
        y="country_name",
        orientation="h",
        color="country_name",
        color_discrete_map=COUNTRY_COLORS,
        text="value",
    )
    figure.update_traces(
        texttemplate=f"%{{x:{fmt}}}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    )
    figure.add_vline(
        x=average,
        line_dash="dot",
        line_color="#64748b",
        annotation_text=f"GCC avg {average:{fmt}}",
        annotation_position="top",
    )
    figure.update_layout(showlegend=False)
    figure.update_xaxes(range=[0, latest["value"].max() * 1.18], title=unit)
    return style_figure(figure, title=f"Latest published year · {latest_year}")


def make_dumbbell(data: pd.DataFrame, unit: str) -> go.Figure:
    first_year = int(data["year"].min())
    last_year = int(data["year"].max())
    endpoints = data[data["year"].isin([first_year, last_year])]
    order = (
        endpoints[endpoints["year"] == last_year]
        .sort_values("value")["country_name"]
        .tolist()
    )
    figure = go.Figure()
    for country in order:
        country_data = endpoints[endpoints["country_name"] == country].sort_values(
            "year"
        )
        figure.add_trace(
            go.Scatter(
                x=country_data["value"],
                y=[country] * len(country_data),
                mode="lines",
                line={"color": "#cbd5e1", "width": 4},
                hoverinfo="skip",
                showlegend=False,
            )
        )
    for year, color, name in (
        [(last_year, "#0f766e", str(last_year))]
        if first_year == last_year
        else [
            (first_year, "#94a3b8", str(first_year)),
            (last_year, "#0f766e", str(last_year)),
        ]
    ):
        year_data = endpoints[endpoints["year"] == year]
        figure.add_trace(
            go.Scatter(
                x=year_data["value"],
                y=year_data["country_name"],
                mode="markers",
                name=name,
                marker={"size": 12, "color": color},
                customdata=year_data["country_name"],
                hovertemplate="%{customdata}: %{x:.1f}<extra></extra>",
            )
        )
    figure.update_yaxes(categoryorder="array", categoryarray=order)
    figure.update_xaxes(title=unit)
    return style_figure(
        figure,
        title=f"Change from {first_year} to {last_year}",
    )


def make_endpoint_compare(data: pd.DataFrame, unit: str) -> go.Figure:
    endpoints = (
        data.sort_values("year")
        .groupby("country_name", as_index=False)
        .agg(first_year=("year", "min"), last_year=("year", "max"))
    )
    first_values = data.merge(
        endpoints[["country_name", "first_year"]],
        left_on=["country_name", "year"],
        right_on=["country_name", "first_year"],
    )
    last_values = data.merge(
        endpoints[["country_name", "last_year"]],
        left_on=["country_name", "year"],
        right_on=["country_name", "last_year"],
    )
    comparison = (
        first_values[["country_name", "year", "value"]]
        .merge(
            last_values[["country_name", "year", "value"]],
            on="country_name",
            suffixes=("_start", "_end"),
        )
        .sort_values("value_end")
    )
    first_year = int(comparison["year_start"].min())
    last_year = int(comparison["year_end"].max())
    figure = go.Figure()
    for row in comparison.itertuples():
        figure.add_trace(
            go.Scatter(
                x=[row.value_start, row.value_end],
                y=[row.country_name, row.country_name],
                mode="lines",
                line={"color": "#cbd5e1", "width": 4},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[row.value_start],
                y=[row.country_name],
                mode="markers",
                marker={"size": 12, "color": "#94a3b8"},
                hovertemplate=(
                    f"{row.country_name}<br>{int(row.year_start)}: "
                    "%{x:.1f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        change = row.value_end - row.value_start
        figure.add_trace(
            go.Scatter(
                x=[row.value_end],
                y=[row.country_name],
                mode="markers+text",
                marker={"size": 12, "color": "#0f766e"},
                text=[f"{row.value_end:.1f} ({change:+.1f})"],
                textposition="middle right",
                hovertemplate=(
                    f"{row.country_name}<br>{int(row.year_end)}: "
                    "%{x:.1f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
    figure.update_xaxes(
        range=[
            comparison["value_start"].min() - 1.5,
            comparison["value_end"].max() + 4,
        ],
        title=unit,
    )
    return style_figure(
        figure,
        title=f"First available year to latest · {first_year}→{last_year}",
    )


def make_small_multiples(
    data: pd.DataFrame, unit: str, mode: str = "line"
) -> go.Figure:
    countries_shown = [
        country for country in COUNTRIES if country in set(data["country_name"])
    ]
    columns = 2
    rows = (len(countries_shown) + columns - 1) // columns
    figure = make_subplots(
        rows=rows,
        cols=columns,
        subplot_titles=countries_shown,
        shared_xaxes=True,
        shared_yaxes=True,
        vertical_spacing=0.16,
        horizontal_spacing=0.1,
    )
    for position, country in enumerate(countries_shown):
        country_data = data[data["country_name"] == country].sort_values("year")
        row = position // columns + 1
        column = position % columns + 1
        if mode == "bar":
            colors = [
                "#c2410c" if value >= 0 else "#0369a1"
                for value in country_data["value"]
            ]
            figure.add_trace(
                go.Bar(
                    x=country_data["year"],
                    y=country_data["value"],
                    marker_color=colors,
                    customdata=[country] * len(country_data),
                    hovertemplate="%{customdata}<br>%{x}: %{y:.1f}%<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=column,
            )
            figure.add_hline(y=0, line={"color": "#64748b", "width": 1}, row=row, col=column)
        else:
            figure.add_trace(
                go.Scatter(
                    x=country_data["year"],
                    y=country_data["value"],
                    mode="lines+markers",
                    line={"color": COUNTRY_COLORS[country], "width": 2.4},
                    marker={"size": 5},
                    customdata=[country] * len(country_data),
                    hovertemplate="%{customdata}<br>%{x}: %{y:.1f}<extra></extra>",
                    showlegend=False,
                ),
                row=row,
                col=column,
            )
    figure = style_figure(figure)
    figure.update_layout(height=max(280, rows * 190), showlegend=False)
    figure.update_annotations(font={"size": 12, "color": "#1c2434"})
    figure.update_xaxes(**year_axis_settings(data), showticklabels=True, showgrid=False)
    figure.update_yaxes(title=None, showgrid=False, title_text=unit)
    return figure


def make_figure(code: str, data: pd.DataFrame, single_year: bool) -> go.Figure:
    meta = INDICATORS[code]
    chart = meta["chart"]
    unit = meta["unit"]
    fmt = meta["format"]

    # When a single year is selected, prefer a ranking view for trend charts too.
    if single_year and chart in {"trend", "small_multiples_line", "small_multiples_bar"}:
        return make_rank_bar(data, unit, fmt)
    if chart == "trend":
        return make_trend(data, unit)
    if chart == "rank":
        return make_rank_bar(data, unit, fmt)
    if chart == "dumbbell":
        return make_dumbbell(data, unit)
    if chart == "compare_endpoints":
        return make_endpoint_compare(data, unit)
    if chart == "small_multiples_bar":
        return make_small_multiples(data, unit, mode="bar")
    return make_small_multiples(data, unit, mode="line")


def coverage_note(code: str) -> str:
    info = COVERAGE.get(code, {})
    first_year = info.get("first_year")
    last_year = info.get("last_year")
    if first_year and last_year:
        return f"Published coverage {first_year}–{last_year}"
    return "Coverage unavailable"


def format_value(code: str, value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:{INDICATORS[code]['format']}}"


def leaderboard_rows(selected_countries: list[str]) -> list:
    focus_codes = ["GDP_PC_USD", "OIL_RENT_PCT", "UNEMP_PCT", "INFLATION_PCT"]
    rows = []
    for code in focus_codes:
        subset = RANK_DATA[
            (RANK_DATA["indicator_code"] == code)
            & (RANK_DATA["country_name"].isin(selected_countries))
        ].copy()
        if subset.empty:
            continue
        meta = INDICATORS[code]
        # For "bad" metrics, best = lowest value.
        if meta["higher_is_better"] is False:
            subset = subset.sort_values("value")
            best = subset.iloc[0]
            worst = subset.iloc[-1]
        else:
            subset = subset.sort_values("value", ascending=False)
            best = subset.iloc[0]
            worst = subset.iloc[-1]
        note = ""
        if code == "OIL_RENT_PCT":
            note = oil_dependence_label(float(best["value"]))
        rows.append(
            html.Div(
                [
                    html.Div(
                        [
                            html.Span(meta["indicator_name"], className="board-label"),
                            html.Strong(
                                f"{best['country_name']} · {format_value(code, best['value'])}"
                            ),
                            html.Span(
                                f"Best in selection · {int(best['year'])}"
                                + (f" · {note}" if note else ""),
                                className="board-meta",
                            ),
                        ]
                    ),
                    html.Div(
                        [
                            html.Span("GCC average", className="board-label"),
                            html.Strong(format_value(code, best["gcc_average"])),
                            html.Span(
                                f"Trailing: {worst['country_name']} · "
                                f"{format_value(code, worst['value'])}",
                                className="board-meta",
                            ),
                        ],
                        className="board-secondary",
                    ),
                ],
                className="board-card",
            )
        )
    return rows


def indicator_card(indicator) -> html.Article:
    code = indicator.indicator_code
    tall = INDICATORS[code]["chart"] in {
        "small_multiples_line",
        "small_multiples_bar",
    }
    return html.Article(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(indicator.indicator_name),
                            html.P(indicator.unit, className="unit"),
                            html.P(coverage_note(code), className="coverage"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Span(id=f"stat-label-{code}"),
                                    html.Strong(id=f"stat-value-{code}"),
                                ],
                                className="stat",
                            ),
                            html.Div(
                                [
                                    html.Span("YoY (latest)"),
                                    html.Strong(id=f"yoy-{code}"),
                                ],
                                className="stat",
                            ),
                        ],
                        className="stat-stack",
                    ),
                ],
                className="card-heading",
            ),
            dcc.Graph(
                id=f"chart-{code}",
                config={"displayModeBar": False, "responsive": True},
                style={"height": "520px" if tall else "340px"},
            ),
            html.Div(id=f"threshold-{code}", className="threshold-row"),
        ],
        className="chart-card",
    )


app = Dash(__name__, title="GCC Statistical Mart")
server = app.server
register_api(server, database=DATABASE)

category_sections = []
for category in INDICATOR_FRAME["category"].drop_duplicates():
    category_rows = INDICATOR_FRAME[INDICATOR_FRAME["category"] == category]
    category_sections.append(
        html.Section(
            [
                html.Div(
                    [
                        html.Span(category.upper(), className="eyebrow"),
                        html.H2(category),
                    ],
                    className="section-heading",
                ),
                html.Div(
                    [indicator_card(row) for row in category_rows.itertuples()],
                    className="chart-grid",
                ),
            ],
            className="category-section",
        )
    )

app.layout = html.Div(
    [
        html.Header(
            [
                html.Div(
                    [
                        html.Span("GCC PEER BENCHMARKING", className="eyebrow"),
                        html.H1("GCC Statistical Mart"),
                        html.P(
                            "Compare Gulf Cooperation Council economies on World Bank "
                            "indicators — with rankings, year-over-year change, and "
                            "oil-dependence thresholds built into the mart."
                        ),
                    ],
                    className="hero-copy",
                ),
                html.Div(
                    [
                        html.Label("Countries"),
                        dcc.Dropdown(
                            id="country-filter",
                            options=[
                                {"label": country, "value": country}
                                for country in COUNTRIES
                            ],
                            value=COUNTRIES,
                            multi=True,
                            clearable=False,
                        ),
                        html.Label("Year or range"),
                        dcc.Dropdown(
                            id="year-filter",
                            options=YEAR_OPTIONS,
                            value="range_latest_10",
                            clearable=False,
                        ),
                        html.Div(
                            [
                                html.Button(
                                    "Export CSV",
                                    id="export-csv-btn",
                                    className="export-btn",
                                    n_clicks=0,
                                ),
                                html.Button(
                                    "Export Excel",
                                    id="export-xlsx-btn",
                                    className="export-btn export-btn-secondary",
                                    n_clicks=0,
                                ),
                            ],
                            className="export-actions",
                        ),
                        dcc.Download(id="download-export"),
                    ],
                    className="filter-panel",
                ),
            ],
            className="hero",
        ),
        html.Main(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.Span("Selection window"),
                                html.Strong(id="selection-window"),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.Span("Countries shown"),
                                html.Strong(id="country-count"),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.Span("Indicators"),
                                html.Strong(str(len(INDICATOR_FRAME))),
                            ],
                            className="summary-card",
                        ),
                        html.Div(
                            [
                                html.Span("Data retrieved"),
                                html.Strong(RETRIEVED_DATE),
                            ],
                            className="summary-card",
                        ),
                    ],
                    className="summary-grid",
                ),
                html.Section(
                    [
                        html.Div(
                            [
                                html.Span("SNAPSHOT", className="eyebrow"),
                                html.H2("Who leads the current selection"),
                                html.P(
                                    "Best/worst and GCC averages use each indicator’s "
                                    "own latest published year — oil rents often lag "
                                    "other series."
                                ),
                            ],
                            className="section-heading",
                        ),
                        html.Div(id="leaderboard", className="board-grid"),
                    ],
                    className="leaderboard-section",
                ),
                html.Div(
                    [
                        "Source: World Bank World Development Indicators. "
                        "Population is stored in millions and GDP in billions of "
                        "current US dollars. JSON API: ",
                        html.A("/api/meta", href="/api/meta", target="_blank"),
                        " · ",
                        html.A(
                            "/api/observations",
                            href="/api/observations",
                            target="_blank",
                        ),
                        " · ",
                        html.A("/api/ranks", href="/api/ranks", target="_blank"),
                        " · ",
                        html.A("/api/export.csv", href="/api/export.csv", target="_blank"),
                        ".",
                    ],
                    className="notice",
                ),
                *category_sections,
            ],
            className="page",
        ),
    ]
)


@app.callback(
    Output("download-export", "data"),
    Input("export-csv-btn", "n_clicks"),
    Input("export-xlsx-btn", "n_clicks"),
    State("country-filter", "value"),
    State("year-filter", "value"),
    prevent_initial_call=True,
)
def export_selection(csv_clicks, xlsx_clicks, selected_countries, selected_year_range):
    if not ctx.triggered_id:
        return None

    selected_countries = selected_countries or COUNTRIES
    first_year, last_year = YEAR_SELECTIONS[selected_year_range]
    frame = load_indicator_export(
        countries=selected_countries,
        year_from=first_year,
        year_to=last_year,
    )
    stamp = (
        str(first_year)
        if first_year == last_year
        else f"{first_year}-{last_year}"
    )
    if ctx.triggered_id == "export-csv-btn":
        return dcc.send_bytes(
            dataframe_to_csv_bytes(frame),
            filename=f"gcc_stat_mart_{stamp}.csv",
        )
    return dcc.send_bytes(
        dataframe_to_xlsx_bytes(frame),
        filename=f"gcc_stat_mart_{stamp}.xlsx",
    )


def average_yoy(code: str, countries: list[str], year: int) -> str:
    subset = YOY_DATA[
        (YOY_DATA["indicator_code"] == code)
        & (YOY_DATA["country_name"].isin(countries))
        & (YOY_DATA["year"] == year)
        & YOY_DATA["yoy_pct"].notna()
    ]
    if subset.empty:
        return "—"
    return f"{subset['yoy_pct'].mean():+.1f}%"


def threshold_chips(code: str, data: pd.DataFrame) -> list:
    if code != "OIL_RENT_PCT" or data.empty:
        return []
    latest_year = int(data["year"].max())
    latest = data[data["year"] == latest_year]
    chips = []
    for row in latest.sort_values("value", ascending=False).itertuples():
        label = oil_dependence_label(float(row.value))
        tone = (
            "warn"
            if label.startswith("High")
            else "mid"
            if label.startswith("Medium")
            else "ok"
        )
        chips.append(
            html.Span(
                f"{row.country_name}: {label} ({row.value:.1f}%)",
                className=f"chip chip-{tone}",
            )
        )
    return chips


outputs = [
    Output("selection-window", "children"),
    Output("country-count", "children"),
    Output("leaderboard", "children"),
]
for indicator in INDICATOR_FRAME.itertuples():
    outputs.extend(
        [
            Output(f"chart-{indicator.indicator_code}", "figure"),
            Output(f"stat-label-{indicator.indicator_code}", "children"),
            Output(f"stat-value-{indicator.indicator_code}", "children"),
            Output(f"yoy-{indicator.indicator_code}", "children"),
            Output(f"threshold-{indicator.indicator_code}", "children"),
        ]
    )


@app.callback(
    outputs,
    Input("country-filter", "value"),
    Input("year-filter", "value"),
)
def update_dashboard(selected_countries, selected_year_range):
    selected_countries = selected_countries or COUNTRIES
    first_year, last_year = YEAR_SELECTIONS[selected_year_range]
    single_year = first_year == last_year
    selection_label = (
        str(first_year) if single_year else f"{first_year}–{last_year}"
    )
    filtered = ALL_DATA[
        ALL_DATA["country_name"].isin(selected_countries)
        & ALL_DATA["year"].between(first_year, last_year)
    ]
    results = [
        selection_label,
        str(len(selected_countries)),
        leaderboard_rows(selected_countries),
    ]

    for indicator in INDICATOR_FRAME.itertuples():
        code = indicator.indicator_code
        indicator_data = filtered[filtered["indicator_code"] == code]
        if indicator_data.empty:
            results.extend(
                [
                    make_no_data_figure(selection_label),
                    f"{selection_label} average",
                    "N/A",
                    "—",
                    [],
                ]
            )
            continue

        latest_year = int(indicator_data["year"].max())
        latest_rows = indicator_data[indicator_data["year"] == latest_year]
        average = latest_rows["value"].mean()
        results.extend(
            [
                make_figure(code, indicator_data, single_year),
                f"{latest_year} selection average",
                format_value(code, average),
                average_yoy(code, selected_countries, latest_year),
                threshold_chips(code, indicator_data),
            ]
        )

    return results


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=PORT)
