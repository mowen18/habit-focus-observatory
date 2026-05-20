"""Altair chart builders for the Streamlit habit app."""

import altair as alt
import pandas as pd


CHART_HEIGHT = 280
CHART_COLOR = "#2E6F95"
CHART_POINT_SIZE = 90


def build_scatter_chart(
    chart_df: pd.DataFrame,
    x_column: str,
    y_column: str,
    x_title: str,
    y_title: str,
) -> alt.Chart:
    """Build a simple Altair scatter plot for a filtered daily relationship."""
    chart_df = chart_df.copy()
    if "checkin_date" in chart_df.columns:
        chart_df["checkin_date"] = pd.to_datetime(chart_df["checkin_date"])
    chart_df[x_column] = pd.to_numeric(chart_df[x_column], errors="coerce")
    chart_df[y_column] = pd.to_numeric(chart_df[y_column], errors="coerce")

    return (
        alt.Chart(chart_df)
        .mark_circle(size=CHART_POINT_SIZE, color=CHART_COLOR)
        .encode(
            x=alt.X(f"{x_column}:Q", title=x_title),
            y=alt.Y(f"{y_column}:Q", title=y_title),
            tooltip=[
                alt.Tooltip("checkin_date:T", title="Date"),
                alt.Tooltip(f"{x_column}:Q", title=x_title),
                alt.Tooltip(f"{y_column}:Q", title=y_title),
            ],
        )
        .properties(height=CHART_HEIGHT)
    )


def build_time_series_chart(
    chart_df: pd.DataFrame,
    y_column: str,
    y_title: str,
) -> alt.Chart:
    """Build a simple Altair line chart with point markers for recent trends."""
    chart_df = chart_df.copy()
    chart_df["checkin_date"] = pd.to_datetime(chart_df["checkin_date"])
    chart_df[y_column] = pd.to_numeric(chart_df[y_column], errors="coerce")

    base_chart = alt.Chart(chart_df).encode(
        x=alt.X("checkin_date:T", title="Date"),
        y=alt.Y(f"{y_column}:Q", title=y_title),
        tooltip=[
            alt.Tooltip("checkin_date:T", title="Date"),
            alt.Tooltip(f"{y_column}:Q", title=y_title),
        ],
    )

    return (
        base_chart.mark_line(color=CHART_COLOR, strokeWidth=2.5)
        + base_chart.mark_circle(size=CHART_POINT_SIZE, color=CHART_COLOR)
    ).properties(height=CHART_HEIGHT)
