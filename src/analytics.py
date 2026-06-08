"""Pure pandas insight summaries for selected habit review windows."""

from typing import List

import pandas as pd


COMPLETENESS_SECTIONS = {
    "has_checkin": "morning check-in",
    "has_deep_work_entry": "deep work",
    "has_caffeine_entry": "caffeine",
    "has_exercise_entry": "exercise",
}


def _has_columns(dataframe: pd.DataFrame, required_columns: List[str]) -> bool:
    """Return True when all required columns are present."""
    return all(column in dataframe.columns for column in required_columns)


def _boolean_series(dataframe: pd.DataFrame, column: str) -> pd.Series:
    """Return a nullable-safe boolean Series for filtering."""
    return dataframe[column].map(lambda value: bool(value) if pd.notna(value) else False)


def _round_1(value: float) -> float:
    """Round to one decimal place while keeping display code simple."""
    return round(float(value), 1)


def _build_completeness_insight(recent_completeness_df: pd.DataFrame) -> List[str]:
    """Summarize all-section completeness and the most missed section."""
    required_columns = [
        "completed_sections",
        "expected_sections",
        *COMPLETENESS_SECTIONS.keys(),
    ]
    if recent_completeness_df.empty or not _has_columns(
        recent_completeness_df,
        required_columns,
    ):
        return []

    total_days = len(recent_completeness_df)
    full_days = int(
        (
            recent_completeness_df["completed_sections"]
            == recent_completeness_df["expected_sections"]
        ).sum()
    )

    missing_counts = {
        column: int((~_boolean_series(recent_completeness_df, column)).sum())
        for column in COMPLETENESS_SECTIONS
    }
    most_missing_column = max(missing_counts, key=missing_counts.get)
    most_missing_count = missing_counts[most_missing_column]

    if most_missing_count == 0:
        return [
            f"{full_days} of {total_days} days in this review window have all sections logged. "
            "The review window is fully logged."
        ]

    section_name = COMPLETENESS_SECTIONS[most_missing_column]
    return [
        f"{full_days} of {total_days} days in this review window have all sections logged. "
        f"The most commonly missing section is {section_name} "
        f"({most_missing_count} day(s))."
    ]


def _build_sleep_focus_insight(analysis_df: pd.DataFrame, min_days: int) -> str:
    """Compare same-day focus on 7+ hour sleep days and shorter-sleep days."""
    required_columns = ["has_checkin", "sleep_hours", "focus_rating"]
    sufficiency_message = (
        "Not enough logged sleep/focus data yet to compare 7+ hour sleep days "
        "with shorter-sleep days."
    )
    if analysis_df.empty or not _has_columns(analysis_df, required_columns):
        return sufficiency_message

    usable_df = analysis_df[
        _boolean_series(analysis_df, "has_checkin")
        & analysis_df["sleep_hours"].notna()
        & analysis_df["focus_rating"].notna()
    ].copy()
    usable_df["sleep_hours"] = pd.to_numeric(usable_df["sleep_hours"], errors="coerce")
    usable_df["focus_rating"] = pd.to_numeric(
        usable_df["focus_rating"],
        errors="coerce",
    )
    usable_df = usable_df.dropna(subset=["sleep_hours", "focus_rating"])

    rested_df = usable_df[usable_df["sleep_hours"] >= 7.0]
    shorter_sleep_df = usable_df[usable_df["sleep_hours"] < 7.0]
    if len(rested_df) < min_days or len(shorter_sleep_df) < min_days:
        return sufficiency_message

    rested_average = rested_df["focus_rating"].mean()
    shorter_sleep_average = shorter_sleep_df["focus_rating"].mean()
    difference = _round_1(abs(rested_average - shorter_sleep_average))

    if rested_average >= shorter_sleep_average:
        return (
            f"Average focus was {difference:.1f} points higher on 7+ hour sleep days "
            "than on shorter-sleep days, "
            f"based on {len(rested_df)} vs {len(shorter_sleep_df)} logged days."
        )

    return (
        f"Average focus was {difference:.1f} points higher on shorter-sleep days "
        "than on 7+ hour sleep days, "
        f"based on {len(shorter_sleep_df)} vs {len(rested_df)} logged days."
    )


def _build_caffeine_sleep_quality_insight(
    analysis_df: pd.DataFrame,
    min_days: int,
) -> str:
    """Compare sleep quality after logged caffeine and no-caffeine days."""
    required_columns = [
        "prior_day_has_caffeine_entry",
        "prior_day_total_caffeine_mg",
        "sleep_quality",
    ]
    sufficiency_message = (
        "Not enough logged caffeine/sleep quality data yet to compare caffeine "
        "days with logged no-caffeine days."
    )
    if analysis_df.empty or not _has_columns(analysis_df, required_columns):
        return sufficiency_message

    usable_df = analysis_df[
        _boolean_series(analysis_df, "prior_day_has_caffeine_entry")
        & analysis_df["prior_day_total_caffeine_mg"].notna()
        & analysis_df["sleep_quality"].notna()
    ].copy()
    usable_df["prior_day_total_caffeine_mg"] = pd.to_numeric(
        usable_df["prior_day_total_caffeine_mg"],
        errors="coerce",
    )
    usable_df["sleep_quality"] = pd.to_numeric(
        usable_df["sleep_quality"],
        errors="coerce",
    )
    usable_df = usable_df.dropna(
        subset=["prior_day_total_caffeine_mg", "sleep_quality"]
    )

    caffeine_df = usable_df[usable_df["prior_day_total_caffeine_mg"] > 0]
    no_caffeine_df = usable_df[usable_df["prior_day_total_caffeine_mg"] == 0]
    if len(caffeine_df) < min_days or len(no_caffeine_df) < min_days:
        return sufficiency_message

    caffeine_average = _round_1(caffeine_df["sleep_quality"].mean())
    no_caffeine_average = _round_1(no_caffeine_df["sleep_quality"].mean())
    return (
        "In the available data, sleep quality averaged "
        f"{caffeine_average:.1f} after caffeine days versus "
        f"{no_caffeine_average:.1f} after no-caffeine days, "
        f"based on {len(caffeine_df)} vs {len(no_caffeine_df)} logged days."
    )


def _build_exercise_energy_insight(analysis_df: pd.DataFrame, min_days: int) -> str:
    """Compare energy after logged exercise and logged no-exercise days."""
    required_columns = [
        "prior_day_has_exercise_entry",
        "prior_day_total_exercise_minutes",
        "energy_rating",
    ]
    sufficiency_message = (
        "Not enough logged exercise/energy data yet to compare exercise days "
        "with logged no-exercise days."
    )
    if analysis_df.empty or not _has_columns(analysis_df, required_columns):
        return sufficiency_message

    usable_df = analysis_df[
        _boolean_series(analysis_df, "prior_day_has_exercise_entry")
        & analysis_df["prior_day_total_exercise_minutes"].notna()
        & analysis_df["energy_rating"].notna()
    ].copy()
    usable_df["prior_day_total_exercise_minutes"] = pd.to_numeric(
        usable_df["prior_day_total_exercise_minutes"],
        errors="coerce",
    )
    usable_df["energy_rating"] = pd.to_numeric(
        usable_df["energy_rating"],
        errors="coerce",
    )
    usable_df = usable_df.dropna(
        subset=["prior_day_total_exercise_minutes", "energy_rating"]
    )

    exercise_df = usable_df[usable_df["prior_day_total_exercise_minutes"] > 0]
    no_exercise_df = usable_df[usable_df["prior_day_total_exercise_minutes"] == 0]
    if len(exercise_df) < min_days or len(no_exercise_df) < min_days:
        return sufficiency_message

    exercise_average = _round_1(exercise_df["energy_rating"].mean())
    no_exercise_average = _round_1(no_exercise_df["energy_rating"].mean())
    return (
        "In the available data, energy averaged "
        f"{exercise_average:.1f} after exercise days versus "
        f"{no_exercise_average:.1f} after no-exercise days, "
        f"based on {len(exercise_df)} vs {len(no_exercise_df)} logged days."
    )


def build_insight_summaries(
    analysis_df: pd.DataFrame,
    recent_completeness_df: pd.DataFrame,
    min_days: int = 3,
) -> List[str]:
    """Build cautious plain-English summaries from selected review-window data."""
    summaries = []
    summaries.extend(_build_completeness_insight(recent_completeness_df))
    summaries.append(_build_sleep_focus_insight(analysis_df, min_days=min_days))
    summaries.append(
        _build_caffeine_sleep_quality_insight(analysis_df, min_days=min_days)
    )
    summaries.append(_build_exercise_energy_insight(analysis_df, min_days=min_days))
    return [summary for summary in summaries if summary]
