from pathlib import Path
import sqlite3
import json

from dash import Dash, Input, Output, dcc, html
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


ROOT = Path(__file__).parent
DATABASE = ROOT / "gcc_stat.db"
REAL_DATA = ROOT / "data" / "raw" / "gcc_indicators_world_bank.csv"
METADATA_FILE = ROOT / "data" / "raw" / "world_bank_metadata.json"
SCHEMA_SCRIPTS = ["01_create_tables.sql", "02_seed_dimensions.sql"]

COUNTRY_COLORS = {
    "Bahrain": "#3b82f6",
    "Kuwait": "#f59e0b",
    "Oman": "#ef4444",
    "Qatar": "#8b5cf6",
    "Saudi Arabia": "#22c55e",
    "United Arab Emirates": "#06b6d4",
}


def ensure_database() -> None:
    source_files = [
        REAL_DATA,
        ROOT / "sql" / "01_create_tables.sql",
        ROOT / "sql" / "02_seed_dimensions.sql",
        ROOT / "sql" / "04_build_facts.sql",
    ]
    if not all(path.exists() for path in source_files):
        raise FileNotFoundError(
            "Real World Bank data is missing. "
            "Run scripts/fetch_world_bank.py first."
        )

    latest_source_change = max(path.stat().st_mtime for path in source_files)
    if DATABASE.exists() and DATABASE.stat().st_mtime >= latest_source_change:
        return

    if DATABASE.exists():
        DATABASE.unlink()

    with sqlite3.connect(DATABASE) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        for script_name in SCHEMA_SCRIPTS:
            script = (ROOT / "sql" / script_name).read_text(encoding="utf-8")
            connection.executescript(script)

        real_data = pd.read_csv(REAL_DATA)
        real_data.to_sql(
            "stg_indicator_raw",
            connection,
            if_exists="append",
            index=False,
        )
        build_script = (ROOT / "sql" / "04_build_facts.sql").read_text(
            encoding="utf-8"
        )
        connection.executescript(build_script)


def run_query(query: str) -> pd.DataFrame:
    with sqlite3.connect(DATABASE) as connection:
        return pd.read_sql_query(query, connection)


ensure_database()
METADATA = json.loads(METADATA_FILE.read_text(encoding="utf-8"))
RETRIEVED_DATE = METADATA["retrieved_at_utc"][:10]

INDICATORS = run_query(
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
FIRST_YEAR = int(ALL_DATA["year"].min())
LAST_YEAR = int(ALL_DATA["year"].max())
DEFAULT_FIRST_YEAR = max(FIRST_YEAR, LAST_YEAR - 10)
YEAR_MARKS = {
    year: str(year)
    for year in sorted(
        set(range(FIRST_YEAR, LAST_YEAR + 1, 5)) | {LAST_YEAR}
    )
}


def style_figure(figure: go.Figure, unit: str) -> go.Figure:
    figure.update_layout(
        height=310,
        margin={"l": 20, "r": 20, "t": 20, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": "#243148", "size": 12},
        hoverlabel={"bgcolor": "#172033", "font_color": "white"},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        xaxis={
            "title": unit,
            "gridcolor": "#e8edf4",
            "zerolinecolor": "#aeb9c9",
        },
        yaxis={"title": None, "gridcolor": "#e8edf4"},
    )
    return figure


def make_heatmap(data: pd.DataFrame, diverging: bool = False) -> go.Figure:
    countries_shown = [
        country for country in COUNTRIES if country in data["country_name"].unique()
    ]
    matrix = data.pivot(
        index="country_name", columns="year", values="value"
    ).reindex(countries_shown)
    colorscale = "RdBu_r" if diverging else "Tealgrn"
    limit = max(abs(matrix.min().min()), abs(matrix.max().max()))
    figure = go.Figure(
        go.Heatmap(
            z=matrix.values,
            x=matrix.columns,
            y=matrix.index,
            colorscale=colorscale,
            zmid=0 if diverging else None,
            zmin=-limit if diverging else None,
            zmax=limit if diverging else None,
            text=matrix.round(1).astype(str).values,
            texttemplate="%{text}" if len(matrix.columns) <= 12 else None,
            hovertemplate="%{y}<br>%{x}: %{z:.1f}<extra></extra>",
            colorbar={"thickness": 10, "len": 0.8},
        )
    )
    return figure


def make_latest_bar(data: pd.DataFrame, unit: str) -> go.Figure:
    latest = data[data["year"] == data["year"].max()].sort_values("value")
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
        texttemplate="%{x:,.1f}",
        textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:,.2f}<extra></extra>",
    )
    figure.update_layout(showlegend=False)
    figure.update_xaxes(range=[0, latest["value"].max() * 1.16])
    return style_figure(figure, unit)


def make_lollipop(data: pd.DataFrame, unit: str) -> go.Figure:
    latest = data[data["year"] == data["year"].max()].sort_values("value")
    figure = go.Figure()
    for row in latest.itertuples():
        figure.add_trace(
            go.Scatter(
                x=[0, row.value],
                y=[row.country_name, row.country_name],
                mode="lines",
                line={"color": "#ccd5e2", "width": 3},
                hoverinfo="skip",
                showlegend=False,
            )
        )
        figure.add_trace(
            go.Scatter(
                x=[row.value],
                y=[row.country_name],
                mode="markers+text",
                marker={
                    "size": 13,
                    "color": COUNTRY_COLORS[row.country_name],
                },
                text=[f"{row.value:,.0f}"],
                textposition="middle right",
                hovertemplate=f"{row.country_name}: %{{x:,.0f}}<extra></extra>",
                showlegend=False,
            )
        )
    figure.update_xaxes(range=[0, latest["value"].max() * 1.18])
    return style_figure(figure, unit)


def make_life_dot_plot(data: pd.DataFrame, unit: str) -> go.Figure:
    latest = data[data["year"] == data["year"].max()].sort_values("value")
    figure = px.scatter(
        latest,
        x="value",
        y="country_name",
        color="country_name",
        color_discrete_map=COUNTRY_COLORS,
        text="value",
    )
    figure.update_traces(
        marker={"size": 14},
        texttemplate="%{x:.1f}",
        textposition="middle right",
        hovertemplate="%{y}: %{x:.1f}<extra></extra>",
    )
    figure.update_layout(showlegend=False)
    figure.update_xaxes(
        range=[latest["value"].min() - 1, latest["value"].max() + 1]
    )
    return style_figure(figure, unit)


def make_dumbbell(data: pd.DataFrame, unit: str) -> go.Figure:
    first_year = int(data["year"].min())
    last_year = int(data["year"].max())
    endpoints = data[data["year"].isin([first_year, last_year])]
    latest = endpoints[endpoints["year"] == last_year].sort_values("value")
    order = latest["country_name"].tolist()
    figure = go.Figure()

    for country in order:
        country_data = endpoints[
            endpoints["country_name"] == country
        ].sort_values("year")
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

    for year, color in [(first_year, "#94a3b8"), (last_year, "#0f9f7f")]:
        year_data = endpoints[endpoints["year"] == year]
        figure.add_trace(
            go.Scatter(
                x=year_data["value"],
                y=year_data["country_name"],
                mode="markers",
                name=str(year),
                marker={"size": 12, "color": color},
                customdata=year_data["country_name"],
                hovertemplate="%{customdata}: %{x:.1f}<extra></extra>",
            )
        )

    figure.update_yaxes(categoryorder="array", categoryarray=order)
    return style_figure(figure, unit)


def make_line_chart(data: pd.DataFrame, unit: str) -> go.Figure:
    figure = px.line(
        data,
        x="year",
        y="value",
        color="country_name",
        markers=True,
        color_discrete_map=COUNTRY_COLORS,
    )
    figure.update_traces(
        hovertemplate="%{fullData.name}<br>%{x}: %{y:,.1f}<extra></extra>"
    )
    return style_figure(figure, unit)


def make_figure(code: str, data: pd.DataFrame, unit: str) -> go.Figure:
    if code == "BIRTH_RATE":
        figure = make_heatmap(data)
        return style_figure(figure, "Year")
    if code == "POP_MN":
        return make_latest_bar(data, unit)
    if code == "GDP_PC_USD":
        return make_lollipop(data, unit)
    if code == "OIL_RENT_PCT":
        return make_latest_bar(data, unit)
    if code == "LIFE_EXP":
        return make_life_dot_plot(data, unit)
    if code == "UNEMP_PCT":
        return make_dumbbell(data, unit)
    if code == "INFLATION_PCT":
        figure = make_heatmap(data, diverging=True)
        return style_figure(figure, "Year")
    return make_line_chart(data, unit)


def indicator_card(indicator) -> html.Article:
    return html.Article(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H3(indicator.indicator_name),
                            html.P(indicator.unit, className="unit"),
                        ]
                    ),
                    html.Div(
                        [
                            html.Span(
                                id=f"average-label-{indicator.indicator_code}"
                            ),
                            html.Strong(id=f"average-{indicator.indicator_code}"),
                        ],
                        className="average",
                    ),
                ],
                className="card-heading",
            ),
            dcc.Graph(
                id=f"chart-{indicator.indicator_code}",
                config={"displayModeBar": False, "responsive": True},
                style={"height": "310px"},
            ),
        ],
        className="chart-card",
    )


app = Dash(__name__, title="GCC Statistical Mart — Dash")
server = app.server

category_sections = []
for category in INDICATORS["category"].drop_duplicates():
    category_rows = INDICATORS[INDICATORS["category"] == category]
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
                    [
                        indicator_card(indicator)
                        for indicator in category_rows.itertuples()
                    ],
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
                        html.Span("ALTERNATIVE PRESENTATION", className="badge"),
                        html.H1("GCC Statistical Mart"),
                        html.P(
                            "Official World Bank indicators for the six GCC "
                            "countries, modeled in SQLite and presented with "
                            "Plotly Dash."
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
                        html.Label("Year range"),
                        dcc.RangeSlider(
                            id="year-filter",
                            min=FIRST_YEAR,
                            max=LAST_YEAR,
                            step=1,
                            value=[DEFAULT_FIRST_YEAR, LAST_YEAR],
                            marks=YEAR_MARKS,
                            allowCross=False,
                        ),
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
                                html.Span("Latest year"),
                                html.Strong(id="latest-year"),
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
                                html.Span("Indicators shown"),
                                html.Strong(str(len(INDICATORS))),
                            ],
                            className="summary-card",
                        ),
                    ],
                    className="summary-grid",
                ),
                html.Div(
                    f"Source: World Bank World Development Indicators · "
                    f"retrieved {RETRIEVED_DATE} · each indicator shows its "
                    f"latest available year.",
                    className="notice",
                ),
                *category_sections,
                html.Footer(
                    [
                        "Built from the gcc_stat.db SQL star schema · ",
                        html.A(
                            "World Bank WDI",
                            href="https://data.worldbank.org/indicator",
                            target="_blank",
                        ),
                    ],
                    className="footer",
                ),
            ],
            className="page",
        ),
    ]
)

outputs = [Output("latest-year", "children"), Output("country-count", "children")]
for indicator in INDICATORS.itertuples():
    outputs.extend(
        [
            Output(f"chart-{indicator.indicator_code}", "figure"),
            Output(f"average-label-{indicator.indicator_code}", "children"),
            Output(f"average-{indicator.indicator_code}", "children"),
        ]
    )


@app.callback(
    outputs,
    Input("country-filter", "value"),
    Input("year-filter", "value"),
)
def update_dashboard(selected_countries, selected_years):
    selected_countries = selected_countries or COUNTRIES
    first_year, last_year = selected_years
    filtered = ALL_DATA[
        ALL_DATA["country_name"].isin(selected_countries)
        & ALL_DATA["year"].between(first_year, last_year)
    ]
    latest_year = int(filtered["year"].max())
    results = [str(latest_year), str(len(selected_countries))]

    for indicator in INDICATORS.itertuples():
        indicator_data = filtered[
            filtered["indicator_code"] == indicator.indicator_code
        ]
        indicator_latest_year = int(indicator_data["year"].max())
        latest_data = indicator_data[
            indicator_data["year"] == indicator_latest_year
        ]
        average = latest_data["value"].mean()
        results.extend(
            [
                make_figure(
                    indicator.indicator_code,
                    indicator_data,
                    indicator.unit,
                ),
                f"{indicator_latest_year} GCC average",
                f"{average:,.1f}",
            ]
        )

    return results


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=8050)
