"""Database read/write helpers for the habit Streamlit app."""

from datetime import date, time
from typing import Optional

import pandas as pd

from src.db import get_connection


_MORNING_DEFAULTS = {
    "sleep_hours": 7.5,
    "sleep_quality": 7,
    "energy_rating": 7,
    "focus_rating": 7,
    "mood_rating": 7,
    "stress_rating": 4,
}
_DEEP_WORK_DEFAULTS = {"deep_work_minutes": 60}
_CAFFEINE_DEFAULTS = {"last_caffeine_time": time(14, 0)}
_EXERCISE_DEFAULTS = {"start_time": time(7, 0)}


def _ensure_daily_checkin_exists(cursor, checkin_date: date) -> None:
    """Create an empty parent daily_checkin row when child rows need it."""
    cursor.execute(
        """
        INSERT INTO daily_checkin (checkin_date)
        VALUES (%s)
        ON CONFLICT (checkin_date) DO NOTHING
        """,
        (checkin_date,),
    )


def save_morning_checkin(payload: dict) -> None:
    """Upsert the morning check-in fields for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_checkin (
                    checkin_date,
                    sleep_hours,
                    sleep_quality,
                    energy_rating,
                    focus_rating,
                    mood_rating,
                    stress_rating,
                    notes
                )
                VALUES (
                    %(checkin_date)s,
                    %(sleep_hours)s,
                    %(sleep_quality)s,
                    %(energy_rating)s,
                    %(focus_rating)s,
                    %(mood_rating)s,
                    %(stress_rating)s,
                    %(notes)s
                )
                ON CONFLICT (checkin_date) DO UPDATE
                SET
                    sleep_hours = EXCLUDED.sleep_hours,
                    sleep_quality = EXCLUDED.sleep_quality,
                    energy_rating = EXCLUDED.energy_rating,
                    focus_rating = EXCLUDED.focus_rating,
                    mood_rating = EXCLUDED.mood_rating,
                    stress_rating = EXCLUDED.stress_rating,
                    notes = EXCLUDED.notes
                """,
                payload,
            )


def save_deep_work_minutes(checkin_date: date, deep_work_minutes: int) -> None:
    """Create or update only the deep_work_minutes field for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO daily_checkin (
                    checkin_date,
                    deep_work_minutes,
                    deep_work_logged
                )
                VALUES (%s, %s, TRUE)
                ON CONFLICT (checkin_date) DO UPDATE
                SET
                    deep_work_minutes = EXCLUDED.deep_work_minutes,
                    deep_work_logged = EXCLUDED.deep_work_logged
                """,
                (checkin_date, deep_work_minutes),
            )


def replace_caffeine_summary(
    checkin_date: date,
    total_caffeine_mg: int,
    last_caffeine_time: time,
) -> None:
    """Replace the stored caffeine summary row for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM caffeine_log WHERE checkin_date = %s",
                (checkin_date,),
            )

            _ensure_daily_checkin_exists(cursor, checkin_date)
            cursor.execute(
                """
                UPDATE daily_checkin
                SET caffeine_logged = TRUE
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )

            if total_caffeine_mg <= 0:
                return

            cursor.execute(
                """
                INSERT INTO caffeine_log (
                    checkin_date,
                    intake_time,
                    source,
                    caffeine_mg
                )
                VALUES (%s, %s, %s, %s)
                """,
                (checkin_date, last_caffeine_time, None, total_caffeine_mg),
            )


def replace_exercise_summary(
    checkin_date: date,
    duration_minutes: int,
    intensity: Optional[str],
    start_time: time,
) -> None:
    """Replace the stored exercise row for one date."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM exercise_log WHERE checkin_date = %s",
                (checkin_date,),
            )

            _ensure_daily_checkin_exists(cursor, checkin_date)
            cursor.execute(
                """
                UPDATE daily_checkin
                SET exercise_logged = TRUE
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )

            if duration_minutes <= 0:
                return

            cursor.execute(
                """
                INSERT INTO exercise_log (
                    checkin_date,
                    exercise_type,
                    duration_minutes,
                    intensity,
                    start_time
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (checkin_date, "Workout", duration_minutes, intensity, start_time),
            )


def load_daily_checkin_values(checkin_date: date) -> dict:
    """Fetch one daily_checkin row for preloading form values."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    sleep_hours,
                    sleep_quality,
                    energy_rating,
                    focus_rating,
                    mood_rating,
                    stress_rating,
                    deep_work_minutes,
                    deep_work_logged,
                    caffeine_logged,
                    exercise_logged,
                    notes
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    if row is None:
        return {}

    deep_work_logged = bool(row[7])

    return {
        "sleep_hours": (
            float(row[0]) if row[0] is not None else _MORNING_DEFAULTS["sleep_hours"]
        ),
        "sleep_quality": (
            row[1] if row[1] is not None else _MORNING_DEFAULTS["sleep_quality"]
        ),
        "energy_rating": (
            row[2] if row[2] is not None else _MORNING_DEFAULTS["energy_rating"]
        ),
        "focus_rating": (
            row[3] if row[3] is not None else _MORNING_DEFAULTS["focus_rating"]
        ),
        "mood_rating": row[4] if row[4] is not None else _MORNING_DEFAULTS["mood_rating"],
        "stress_rating": (
            row[5] if row[5] is not None else _MORNING_DEFAULTS["stress_rating"]
        ),
        "deep_work_minutes": (
            row[6]
            if deep_work_logged and row[6] is not None
            else _DEEP_WORK_DEFAULTS["deep_work_minutes"]
        ),
        "deep_work_logged": deep_work_logged,
        "caffeine_logged": bool(row[8]),
        "exercise_logged": bool(row[9]),
        "notes": row[10] or "",
    }


def load_caffeine_summary_values(checkin_date: date) -> dict:
    """Fetch one caffeine summary row for preloading the caffeine form."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT caffeine_logged
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            logged_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    caffeine_mg,
                    intake_time
                FROM caffeine_log
                WHERE checkin_date = %s
                ORDER BY caffeine_id DESC
                LIMIT 1
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    caffeine_logged = bool(logged_row[0]) if logged_row is not None else False
    if not caffeine_logged:
        return {"caffeine_logged": False}

    return {
        "caffeine_logged": True,
        "total_caffeine_mg": row[0] if row is not None else 0,
        "last_caffeine_time": (
            row[1]
            if row is not None and row[1] is not None
            else _CAFFEINE_DEFAULTS["last_caffeine_time"]
        ),
    }


def load_exercise_summary_values(checkin_date: date) -> dict:
    """Fetch one exercise summary row for preloading the exercise form."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT exercise_logged
                FROM daily_checkin
                WHERE checkin_date = %s
                """,
                (checkin_date,),
            )
            logged_row = cursor.fetchone()

            cursor.execute(
                """
                SELECT
                    duration_minutes,
                    intensity,
                    start_time
                FROM exercise_log
                WHERE checkin_date = %s
                ORDER BY exercise_id DESC
                LIMIT 1
                """,
                (checkin_date,),
            )
            row = cursor.fetchone()

    exercise_logged = bool(logged_row[0]) if logged_row is not None else False
    if not exercise_logged:
        return {"exercise_logged": False}

    return {
        "exercise_logged": True,
        "duration_minutes": row[0] if row is not None else 0,
        "intensity": row[1] if row is not None and row[1] is not None else "",
        "start_time": (
            row[2]
            if row is not None and row[2] is not None
            else _EXERCISE_DEFAULTS["start_time"]
        ),
    }


def load_recent_daily_metrics(
    limit: int = 14,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Fetch daily metrics for either a recent limit or a fixed date range."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if start_date is not None and end_date is not None:
                cursor.execute(
                    """
                    SELECT
                        checkin_date,
                        sleep_hours,
                        sleep_quality,
                        energy_rating,
                        focus_rating,
                        mood_rating,
                        stress_rating,
                        deep_work_minutes,
                        total_caffeine_mg,
                        caffeine_after_2pm,
                        total_exercise_minutes,
                        high_intensity_flag
                    FROM daily_metrics_vw
                    WHERE checkin_date BETWEEN %s AND %s
                    ORDER BY checkin_date
                    """,
                    (start_date, end_date),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        checkin_date,
                        sleep_hours,
                        sleep_quality,
                        energy_rating,
                        focus_rating,
                        mood_rating,
                        stress_rating,
                        deep_work_minutes,
                        total_caffeine_mg,
                        caffeine_after_2pm,
                        total_exercise_minutes,
                        high_intensity_flag
                    FROM daily_metrics_vw
                    ORDER BY checkin_date DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    metrics_df = pd.DataFrame(rows, columns=columns)
    return metrics_df.sort_values("checkin_date").reset_index(drop=True)


def load_recent_daily_completeness(
    limit: int = 14,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Fetch completeness rows for either a recent limit or fixed date range."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if start_date is not None and end_date is not None:
                cursor.execute(
                    """
                    WITH review_dates AS (
                        SELECT
                            generate_series(
                                %s::DATE,
                                %s::DATE,
                                INTERVAL '1 day'
                            )::DATE AS checkin_date
                    )
                    SELECT
                        review_dates.checkin_date,
                        COALESCE(dc.has_checkin, FALSE) AS has_checkin,
                        COALESCE(dc.has_deep_work_entry, FALSE) AS has_deep_work_entry,
                        COALESCE(dc.has_caffeine_entry, FALSE) AS has_caffeine_entry,
                        COALESCE(dc.has_exercise_entry, FALSE) AS has_exercise_entry,
                        COALESCE(dc.completed_sections, 0) AS completed_sections,
                        COALESCE(dc.expected_sections, 4) AS expected_sections,
                        COALESCE(dc.completeness_pct, 0.0) AS completeness_pct
                    FROM review_dates
                    LEFT JOIN daily_completeness_vw AS dc
                        ON review_dates.checkin_date = dc.checkin_date
                    ORDER BY review_dates.checkin_date
                    """,
                    (start_date, end_date),
                )
            else:
                cursor.execute(
                    """
                    WITH recent_dates AS (
                        SELECT
                            generate_series(
                                CURRENT_DATE - (%s::INTEGER - 1),
                                CURRENT_DATE,
                                INTERVAL '1 day'
                            )::DATE AS checkin_date
                    )
                    SELECT
                        recent_dates.checkin_date,
                        COALESCE(dc.has_checkin, FALSE) AS has_checkin,
                        COALESCE(dc.has_deep_work_entry, FALSE) AS has_deep_work_entry,
                        COALESCE(dc.has_caffeine_entry, FALSE) AS has_caffeine_entry,
                        COALESCE(dc.has_exercise_entry, FALSE) AS has_exercise_entry,
                        COALESCE(dc.completed_sections, 0) AS completed_sections,
                        COALESCE(dc.expected_sections, 4) AS expected_sections,
                        COALESCE(dc.completeness_pct, 0.0) AS completeness_pct
                    FROM recent_dates
                    LEFT JOIN daily_completeness_vw AS dc
                        ON recent_dates.checkin_date = dc.checkin_date
                    ORDER BY recent_dates.checkin_date DESC
                    """,
                    (limit,),
                )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    completeness_df = pd.DataFrame(rows, columns=columns)
    return completeness_df.sort_values("checkin_date").reset_index(drop=True)


def load_analysis_daily_data(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Fetch analysis-ready outcomes and prior-day behavior inputs."""
    with get_connection() as connection:
        with connection.cursor() as cursor:
            if start_date is not None and end_date is not None:
                cursor.execute(
                    """
                    SELECT
                        current_day.checkin_date,
                        current_day.sleep_hours,
                        current_day.sleep_quality,
                        current_day.energy_rating,
                        current_day.focus_rating,
                        current_day.mood_rating,
                        current_day.stress_rating,
                        current_completeness.has_checkin,
                        prior_day.deep_work_minutes AS prior_day_deep_work_minutes,
                        prior_day.total_caffeine_mg AS prior_day_total_caffeine_mg,
                        prior_day.total_exercise_minutes AS prior_day_total_exercise_minutes,
                        prior_completeness.has_deep_work_entry AS prior_day_has_deep_work_entry,
                        prior_completeness.has_caffeine_entry AS prior_day_has_caffeine_entry,
                        prior_completeness.has_exercise_entry AS prior_day_has_exercise_entry
                    FROM daily_metrics_vw AS current_day
                    LEFT JOIN daily_completeness_vw AS current_completeness
                        ON current_day.checkin_date = current_completeness.checkin_date
                    LEFT JOIN daily_metrics_vw AS prior_day
                        ON prior_day.checkin_date = current_day.checkin_date - 1
                    LEFT JOIN daily_completeness_vw AS prior_completeness
                        ON prior_completeness.checkin_date = current_day.checkin_date - 1
                    WHERE current_day.checkin_date BETWEEN %s AND %s
                    ORDER BY current_day.checkin_date
                    """,
                    (start_date, end_date),
                )
            else:
                cursor.execute(
                    """
                    SELECT
                        current_day.checkin_date,
                        current_day.sleep_hours,
                        current_day.sleep_quality,
                        current_day.energy_rating,
                        current_day.focus_rating,
                        current_day.mood_rating,
                        current_day.stress_rating,
                        current_completeness.has_checkin,
                        prior_day.deep_work_minutes AS prior_day_deep_work_minutes,
                        prior_day.total_caffeine_mg AS prior_day_total_caffeine_mg,
                        prior_day.total_exercise_minutes AS prior_day_total_exercise_minutes,
                        prior_completeness.has_deep_work_entry AS prior_day_has_deep_work_entry,
                        prior_completeness.has_caffeine_entry AS prior_day_has_caffeine_entry,
                        prior_completeness.has_exercise_entry AS prior_day_has_exercise_entry
                    FROM daily_metrics_vw AS current_day
                    LEFT JOIN daily_completeness_vw AS current_completeness
                        ON current_day.checkin_date = current_completeness.checkin_date
                    LEFT JOIN daily_metrics_vw AS prior_day
                        ON prior_day.checkin_date = current_day.checkin_date - 1
                    LEFT JOIN daily_completeness_vw AS prior_completeness
                        ON prior_completeness.checkin_date = current_day.checkin_date - 1
                    ORDER BY current_day.checkin_date
                    """
                )
            rows = cursor.fetchall()
            columns = [column.name for column in cursor.description]

    if not rows:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(rows, columns=columns)
