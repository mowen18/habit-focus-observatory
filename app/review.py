"""Recent Trends & Review rendering for the Streamlit habit app."""

import pandas as pd
import streamlit as st

from app.charts import build_scatter_chart, build_time_series_chart
from src.habit_repository import (
    load_analysis_daily_data,
    load_recent_daily_completeness,
    load_recent_daily_metrics,
)


def _format_average(series: pd.Series, decimals: int = 1) -> str:
    """Format an average metric while handling missing values cleanly."""
    average_value = series.mean()
    if pd.isna(average_value):
        return "N/A"
    return f"{average_value:.{decimals}f}"


def _format_logged_status(value: bool) -> str:
    """Display completeness flags with simple human-friendly labels."""
    return "Logged" if bool(value) else "Not logged"


def prepare_completeness_display_data(recent_completeness_df: pd.DataFrame) -> pd.DataFrame:
    """Return a small recent completeness table ready for display."""
    display_df = recent_completeness_df.copy()
    status_columns = [
        "has_checkin",
        "has_deep_work_entry",
        "has_caffeine_entry",
        "has_exercise_entry",
    ]
    for column in status_columns:
        display_df[column] = display_df[column].map(_format_logged_status)

    display_df["completeness_pct"] = display_df["completeness_pct"].map(
        lambda value: f"{float(value):.1f}%"
    )

    return display_df.rename(
        columns={
            "checkin_date": "Date",
            "has_checkin": "Morning check-in",
            "has_deep_work_entry": "Deep work",
            "has_caffeine_entry": "Caffeine",
            "has_exercise_entry": "Exercise",
            "completed_sections": "Completed sections",
            "expected_sections": "Expected sections",
            "completeness_pct": "Completeness",
        }
    )


def prepare_trend_chart_data(
    recent_metrics_df: pd.DataFrame,
    value_column: str,
) -> pd.DataFrame:
    """Return typed recent metric data for Altair trend charts."""
    chart_df = recent_metrics_df[["checkin_date", value_column]].copy()
    chart_df["checkin_date"] = pd.to_datetime(chart_df["checkin_date"])
    chart_df[value_column] = pd.to_numeric(chart_df[value_column], errors="coerce")
    return chart_df.sort_values("checkin_date").reset_index(drop=True)


def prepare_sleep_focus_analysis_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return same-day morning rows with usable sleep and focus values."""
    sleep_focus_df = analysis_df[
        analysis_df["has_checkin"]
        & analysis_df["sleep_hours"].notna()
        & analysis_df["focus_rating"].notna()
    ][["checkin_date", "sleep_hours", "focus_rating"]].copy()
    return sleep_focus_df.sort_values("checkin_date").reset_index(drop=True)


def prepare_caffeine_sleep_quality_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return prior-day caffeine inputs aligned to current-day sleep quality."""
    caffeine_sleep_df = analysis_df[
        analysis_df["prior_day_has_caffeine_entry"]
        & analysis_df["prior_day_total_caffeine_mg"].notna()
        & analysis_df["sleep_quality"].notna()
    ][["checkin_date", "prior_day_total_caffeine_mg", "sleep_quality"]].copy()
    return caffeine_sleep_df.sort_values("checkin_date").reset_index(drop=True)


def prepare_exercise_energy_data(analysis_df: pd.DataFrame) -> pd.DataFrame:
    """Return prior-day exercise inputs aligned to current-day energy ratings."""
    exercise_energy_df = analysis_df[
        analysis_df["prior_day_has_exercise_entry"]
        & analysis_df["prior_day_total_exercise_minutes"].notna()
        & analysis_df["energy_rating"].notna()
    ][["checkin_date", "prior_day_total_exercise_minutes", "energy_rating"]].copy()
    return exercise_energy_df.sort_values("checkin_date").reset_index(drop=True)


def render_recent_review() -> None:
    """Render the Recent Trends & Review section."""
    st.divider()
    st.subheader("Recent Trends & Review")

    try:
        recent_metrics_df = load_recent_daily_metrics(limit=14)
        recent_completeness_df = load_recent_daily_completeness(limit=14)
        analysis_df = load_analysis_daily_data()
    except Exception as exc:
        st.error(
            "We couldn't load the recent trends section. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
        return

    if recent_metrics_df.empty:
        st.info("No data yet. Save a check-in above to populate the recent review section.")
        return

    recent_7d_df = recent_metrics_df.tail(7)

    metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)
    metric_col_1.metric(
        "Avg sleep hours",
        _format_average(recent_7d_df["sleep_hours"], decimals=2),
    )
    metric_col_2.metric(
        "Avg focus rating",
        _format_average(recent_7d_df["focus_rating"]),
    )
    metric_col_3.metric(
        "Avg energy rating",
        _format_average(recent_7d_df["energy_rating"]),
    )
    metric_col_4.metric(
        "Avg deep work minutes",
        _format_average(recent_7d_df["deep_work_minutes"]),
    )

    st.write("Sleep hours over time")
    sleep_chart_df = prepare_trend_chart_data(
        recent_metrics_df,
        value_column="sleep_hours",
    )
    if sleep_chart_df["sleep_hours"].dropna().empty:
        st.info("No sleep-hour data available for the recent chart yet.")
    else:
        st.altair_chart(
            build_time_series_chart(
                sleep_chart_df,
                y_column="sleep_hours",
                y_title="Sleep hours",
            ),
            use_container_width=True,
        )

    st.write("Focus rating over time")
    focus_chart_df = prepare_trend_chart_data(
        recent_metrics_df,
        value_column="focus_rating",
    )
    st.altair_chart(
        build_time_series_chart(
            focus_chart_df,
            y_column="focus_rating",
            y_title="Focus rating",
        ),
        use_container_width=True,
    )

    st.write("Deep work minutes over time")
    deep_work_chart_df = prepare_trend_chart_data(
        recent_metrics_df,
        value_column="deep_work_minutes",
    )
    st.altair_chart(
        build_time_series_chart(
            deep_work_chart_df,
            y_column="deep_work_minutes",
            y_title="Deep work minutes",
        ),
        use_container_width=True,
    )

    st.write("Relationship spot checks")

    sleep_focus_df = prepare_sleep_focus_analysis_data(analysis_df)
    st.write("Sleep hours vs same-day focus rating")
    if len(sleep_focus_df) < 2:
        st.info(
            "Add at least two morning check-ins with sleep hours and focus ratings to see this chart."
        )
    else:
        st.caption(f"Using {len(sleep_focus_df)} day(s) with a real morning check-in.")
        st.altair_chart(
            build_scatter_chart(
                sleep_focus_df,
                x_column="sleep_hours",
                y_column="focus_rating",
                x_title="Sleep hours",
                y_title="Same-day focus rating",
            ),
            use_container_width=True,
        )

    caffeine_sleep_df = prepare_caffeine_sleep_quality_data(analysis_df)
    st.write("Yesterday total caffeine mg vs today sleep quality")
    if len(caffeine_sleep_df) < 2:
        st.info(
            "Add at least two rows with yesterday's explicitly logged caffeine and today's sleep quality to see this chart."
        )
    else:
        st.caption(
            f"Using {len(caffeine_sleep_df)} day(s) where yesterday's caffeine was explicitly logged and today's sleep quality is present."
        )
        st.altair_chart(
            build_scatter_chart(
                caffeine_sleep_df,
                x_column="prior_day_total_caffeine_mg",
                y_column="sleep_quality",
                x_title="Yesterday total caffeine mg",
                y_title="Today sleep quality",
            ),
            use_container_width=True,
        )

    exercise_energy_df = prepare_exercise_energy_data(analysis_df)
    st.write("Yesterday total exercise minutes vs today energy rating")
    if len(exercise_energy_df) < 2:
        st.info(
            "Add at least two rows with yesterday's explicitly logged exercise and today's energy rating to see this chart."
        )
    else:
        st.caption(
            f"Using {len(exercise_energy_df)} day(s) where yesterday's exercise was explicitly logged and today's energy rating is present."
        )
        st.altair_chart(
            build_scatter_chart(
                exercise_energy_df,
                x_column="prior_day_total_exercise_minutes",
                y_column="energy_rating",
                x_title="Yesterday total exercise minutes",
                y_title="Today energy rating",
            ),
            use_container_width=True,
        )

    st.write("Data completeness")
    full_data_days = int(
        (
            recent_completeness_df["completed_sections"]
            == recent_completeness_df["expected_sections"]
        ).sum()
    )
    completeness_metric_col_1, completeness_metric_col_2 = st.columns(2)
    completeness_metric_col_3, completeness_metric_col_4 = st.columns(2)
    completeness_metric_col_1.metric(
        "Full data days",
        f"{full_data_days}/{len(recent_completeness_df)}",
    )
    completeness_metric_col_2.metric(
        "Missing deep work",
        int((~recent_completeness_df["has_deep_work_entry"]).sum()),
    )
    completeness_metric_col_3.metric(
        "Missing caffeine",
        int((~recent_completeness_df["has_caffeine_entry"]).sum()),
    )
    completeness_metric_col_4.metric(
        "Missing exercise",
        int((~recent_completeness_df["has_exercise_entry"]).sum()),
    )

    completeness_display_df = prepare_completeness_display_data(
        recent_completeness_df.sort_values("checkin_date", ascending=False)
    )
    st.dataframe(
        completeness_display_df,
        use_container_width=True,
        hide_index=True,
    )

    st.write("Recent daily logs")
    st.dataframe(
        recent_metrics_df.sort_values("checkin_date", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
