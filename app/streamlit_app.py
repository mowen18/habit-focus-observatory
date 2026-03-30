"""Streamlit app for a simple morning habit and focus workflow."""

from datetime import date, time, timedelta
from pathlib import Path
import sys
from typing import Optional

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db import get_connection


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def _clean_text(value: str):
    """Normalize blank text inputs to None."""
    cleaned = value.strip()
    return cleaned or None


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
                    deep_work_minutes
                )
                VALUES (%s, %s)
                ON CONFLICT (checkin_date) DO UPDATE
                SET deep_work_minutes = EXCLUDED.deep_work_minutes
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

            if total_caffeine_mg <= 0:
                return

            _ensure_daily_checkin_exists(cursor, checkin_date)
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

            if duration_minutes <= 0:
                return

            _ensure_daily_checkin_exists(cursor, checkin_date)
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


def _render_save_error(exc: Exception) -> None:
    """Show a friendly save error for this MVP app."""
    st.error(
        "We couldn't save this entry. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )


st.set_page_config(page_title="Habit Focus Observatory", layout="centered")
st.title("Habit Focus Observatory")
st.caption("Simple morning workflow for the MVP.")
st.write(
    "Use the forms below to record today's check-in and yesterday's supporting summaries."
)

st.subheader("1. Today Morning Check-in")
with st.form("today_morning_checkin_form"):
    morning_date_col, morning_sleep_col = st.columns(2)
    morning_checkin_date = morning_date_col.date_input(
        "Check-in date",
        value=TODAY,
        key="morning_checkin_date",
    )
    morning_sleep_hours = morning_sleep_col.number_input(
        "Sleep hours",
        min_value=0.0,
        max_value=24.0,
        value=7.5,
        step=0.25,
        key="morning_sleep_hours",
    )

    morning_rating_col_1, morning_rating_col_2, morning_rating_col_3 = st.columns(3)
    morning_sleep_quality = morning_rating_col_1.number_input(
        "Sleep quality (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="morning_sleep_quality",
    )
    morning_energy_rating = morning_rating_col_2.number_input(
        "Energy rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="morning_energy_rating",
    )
    morning_focus_rating = morning_rating_col_3.number_input(
        "Focus rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="morning_focus_rating",
    )

    morning_rating_col_4, morning_rating_col_5 = st.columns(2)
    morning_mood_rating = morning_rating_col_4.number_input(
        "Mood rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="morning_mood_rating",
    )
    morning_stress_rating = morning_rating_col_5.number_input(
        "Stress rating (1-10)",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        key="morning_stress_rating",
    )
    morning_notes = st.text_area("Notes", key="morning_notes")

    morning_submitted = st.form_submit_button("Save today's morning check-in")

if morning_submitted:
    morning_payload = {
        "checkin_date": morning_checkin_date,
        "sleep_hours": round(float(morning_sleep_hours), 2),
        "sleep_quality": int(morning_sleep_quality),
        "energy_rating": int(morning_energy_rating),
        "focus_rating": int(morning_focus_rating),
        "mood_rating": int(morning_mood_rating),
        "stress_rating": int(morning_stress_rating),
        "notes": _clean_text(morning_notes),
    }
    try:
        save_morning_checkin(morning_payload)
        st.success(f"Saved today's morning check-in for {morning_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("2. Yesterday Deep Work")
with st.form("yesterday_deep_work_form"):
    deep_work_col_1, deep_work_col_2 = st.columns(2)
    deep_work_date = deep_work_col_1.date_input(
        "Check-in date",
        value=YESTERDAY,
        key="deep_work_date",
    )
    deep_work_minutes = deep_work_col_2.number_input(
        "Deep work minutes",
        min_value=0,
        value=60,
        step=15,
        key="deep_work_minutes",
    )

    deep_work_submitted = st.form_submit_button("Save yesterday's deep work")

if deep_work_submitted:
    try:
        save_deep_work_minutes(deep_work_date, int(deep_work_minutes))
        st.success(f"Saved deep work for {deep_work_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("3. Yesterday Caffeine Summary")
with st.form("yesterday_caffeine_form"):
    caffeine_date_col, caffeine_total_col = st.columns(2)
    caffeine_checkin_date = caffeine_date_col.date_input(
        "Check-in date",
        value=YESTERDAY,
        key="caffeine_checkin_date",
    )
    total_caffeine_mg = caffeine_total_col.number_input(
        "Total caffeine mg",
        min_value=0,
        value=0,
        step=5,
        key="total_caffeine_mg",
    )
    last_caffeine_time = st.time_input(
        "Last caffeine time",
        value=time(14, 0),
        key="last_caffeine_time",
    )

    caffeine_submitted = st.form_submit_button("Save yesterday's caffeine summary")

if caffeine_submitted:
    try:
        replace_caffeine_summary(
            caffeine_checkin_date,
            int(total_caffeine_mg),
            last_caffeine_time,
        )
        if int(total_caffeine_mg) > 0:
            st.success(f"Saved caffeine summary for {caffeine_checkin_date.isoformat()}.")
        else:
            st.success(f"Cleared caffeine entries for {caffeine_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)

st.subheader("4. Yesterday Exercise")
with st.form("yesterday_exercise_form"):
    exercise_date_col, exercise_duration_col = st.columns(2)
    exercise_checkin_date = exercise_date_col.date_input(
        "Check-in date",
        value=YESTERDAY,
        key="exercise_checkin_date",
    )
    exercise_duration_minutes = exercise_duration_col.number_input(
        "Duration minutes",
        min_value=0,
        value=0,
        step=5,
        key="exercise_duration_minutes",
    )

    exercise_intensity_col, exercise_time_col = st.columns(2)
    exercise_intensity = exercise_intensity_col.selectbox(
        "Intensity",
        options=["", "low", "moderate", "high"],
        key="exercise_intensity",
    )
    exercise_start_time = exercise_time_col.time_input(
        "Start time",
        value=time(7, 0),
        key="exercise_start_time",
    )

    exercise_submitted = st.form_submit_button("Save yesterday's exercise")

if exercise_submitted:
    try:
        replace_exercise_summary(
            exercise_checkin_date,
            int(exercise_duration_minutes),
            exercise_intensity or None,
            exercise_start_time,
        )
        if int(exercise_duration_minutes) > 0:
            st.success(f"Saved exercise for {exercise_checkin_date.isoformat()}.")
        else:
            st.success(f"Cleared exercise entries for {exercise_checkin_date.isoformat()}.")
    except Exception as exc:
        _render_save_error(exc)
