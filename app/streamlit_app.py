"""Streamlit app for manual daily check-in, caffeine, and exercise entry."""

from datetime import time
from pathlib import Path
import sys

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.db import get_connection


def _clean_text(value: str):
    """Normalize blank text inputs to None."""
    cleaned = value.strip()
    return cleaned or None


def _collect_caffeine_rows(intake_time, caffeine_mg):
    """Return a single optional caffeine row when caffeine is entered."""
    if int(caffeine_mg) <= 0:
        return []

    return [
        {
            "intake_time": intake_time,
            "source": None,
            "caffeine_mg": int(caffeine_mg),
        }
    ]


def _collect_exercise_rows(duration_minutes, intensity, start_time):
    """Return a single optional exercise row when exercise is entered."""
    cleaned_intensity = intensity or None
    duration_minutes = int(duration_minutes)
    has_data = duration_minutes > 0 or cleaned_intensity is not None

    if not has_data:
        return []

    if duration_minutes <= 0:
        raise ValueError("Exercise duration must be greater than 0 when logging exercise.")

    return [
        {
            "exercise_type": "Workout",
            "duration_minutes": duration_minutes,
            "intensity": cleaned_intensity,
            "start_time": start_time,
        }
    ]


def save_daily_log(payload: dict, caffeine_rows: list[dict], exercise_rows: list[dict]) -> None:
    """Save one daily check-in and refresh its related child rows."""
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
                    deep_work_minutes,
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
                    %(deep_work_minutes)s,
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
                    deep_work_minutes = EXCLUDED.deep_work_minutes,
                    notes = EXCLUDED.notes
                """,
                payload,
            )

            cursor.execute(
                "DELETE FROM caffeine_log WHERE checkin_date = %s",
                (payload["checkin_date"],),
            )
            for row in caffeine_rows:
                cursor.execute(
                    """
                    INSERT INTO caffeine_log (
                        checkin_date,
                        intake_time,
                        source,
                        caffeine_mg
                    )
                    VALUES (
                        %(checkin_date)s,
                        %(intake_time)s,
                        %(source)s,
                        %(caffeine_mg)s
                    )
                    """,
                    {"checkin_date": payload["checkin_date"], **row},
                )

            cursor.execute(
                "DELETE FROM exercise_log WHERE checkin_date = %s",
                (payload["checkin_date"],),
            )
            for row in exercise_rows:
                cursor.execute(
                    """
                    INSERT INTO exercise_log (
                        checkin_date,
                        exercise_type,
                        duration_minutes,
                        intensity,
                        start_time
                    )
                    VALUES (
                        %(checkin_date)s,
                        %(exercise_type)s,
                        %(duration_minutes)s,
                        %(intensity)s,
                        %(start_time)s
                    )
                    """,
                    {"checkin_date": payload["checkin_date"], **row},
                )


st.set_page_config(page_title="Habit Focus Observatory", layout="centered")
st.title("Habit Focus Observatory")
st.caption("Manual daily check-in entry for the MVP.")
st.write("Log a daily check-in with optional caffeine and exercise rows for the same date.")

with st.form("daily_checkin_form"):
    st.subheader("Daily check-in")
    date_col, sleep_col = st.columns(2)
    checkin_date = date_col.date_input("Check-in date", key="checkin_date")
    sleep_hours = sleep_col.number_input(
        "Sleep hours",
        min_value=0.0,
        max_value=24.0,
        value=7.5,
        step=0.25,
        key="sleep_hours",
    )

    ratings_col_1, ratings_col_2, ratings_col_3 = st.columns(3)
    sleep_quality = ratings_col_1.number_input(
        "Sleep quality (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="sleep_quality",
    )
    energy_rating = ratings_col_2.number_input(
        "Energy rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="energy_rating",
    )
    focus_rating = ratings_col_3.number_input(
        "Focus rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="focus_rating",
    )

    ratings_col_4, ratings_col_5, deep_work_col = st.columns(3)
    mood_rating = ratings_col_4.number_input(
        "Mood rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="mood_rating",
    )
    stress_rating = ratings_col_5.number_input(
        "Stress rating (1-10)",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        key="stress_rating",
    )
    deep_work_minutes = deep_work_col.number_input(
        "Deep work minutes",
        min_value=0,
        value=60,
        step=15,
        key="deep_work_minutes",
    )
    notes = st.text_area("Notes", key="notes")

    st.subheader("Optional caffeine entry")
    caffeine_cols = st.columns(2)
    caffeine_intake_time = caffeine_cols[0].time_input(
        "Caffeine time",
        value=time(8, 0),
        key="caffeine_intake_time",
    )
    caffeine_mg = caffeine_cols[1].number_input(
        "Caffeine mg",
        min_value=0,
        value=0,
        step=5,
        key="caffeine_mg",
    )

    st.subheader("Optional exercise entry")
    exercise_cols = st.columns(3)
    exercise_duration = exercise_cols[0].number_input(
        "Exercise minutes",
        min_value=0,
        value=0,
        step=5,
        key="exercise_duration",
    )
    exercise_intensity = exercise_cols[1].selectbox(
        "Exercise intensity",
        options=["", "low", "moderate", "high"],
        key="exercise_intensity",
    )
    exercise_start_time = exercise_cols[2].time_input(
        "Exercise start",
        value=time(7, 0),
        key="exercise_start_time",
    )

    submitted = st.form_submit_button("Save daily check-in")

if submitted:
    daily_payload = {
        "checkin_date": checkin_date,
        "sleep_hours": round(float(sleep_hours), 2),
        "sleep_quality": int(sleep_quality),
        "energy_rating": int(energy_rating),
        "focus_rating": int(focus_rating),
        "mood_rating": int(mood_rating),
        "stress_rating": int(stress_rating),
        "deep_work_minutes": int(deep_work_minutes),
        "notes": notes.strip() or None,
    }
    try:
        caffeine_rows = _collect_caffeine_rows(caffeine_intake_time, caffeine_mg)
        exercise_rows = _collect_exercise_rows(
            exercise_duration,
            exercise_intensity,
            exercise_start_time,
        )
        save_daily_log(daily_payload, caffeine_rows, exercise_rows)
        st.success(
            f"Saved daily check-in for {checkin_date.isoformat()} with "
            f"{len(caffeine_rows)} caffeine entries and {len(exercise_rows)} exercise entries."
        )
    except ValueError as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(
            "We couldn't save this daily log. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
