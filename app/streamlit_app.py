"""Streamlit app for manual daily check-in entry."""

import streamlit as st

from src.db import get_connection


def save_daily_checkin(payload: dict) -> None:
    """Insert or update a single daily_checkin row."""
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


st.set_page_config(page_title="Habit Focus Observatory", layout="centered")
st.title("Habit Focus Observatory")
st.caption("Manual daily check-in entry for the MVP.")
st.write("Log one daily check-in row in Postgres using the form below.")

with st.form("daily_checkin_form"):
    checkin_date = st.date_input("Check-in date", key="checkin_date")
    sleep_hours = st.number_input(
        "Sleep hours",
        min_value=0.0,
        max_value=24.0,
        value=7.5,
        step=0.25,
        key="sleep_hours",
    )
    sleep_quality = st.number_input(
        "Sleep quality (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="sleep_quality",
    )
    energy_rating = st.number_input(
        "Energy rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="energy_rating",
    )
    focus_rating = st.number_input(
        "Focus rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="focus_rating",
    )
    mood_rating = st.number_input(
        "Mood rating (1-10)",
        min_value=1,
        max_value=10,
        value=7,
        step=1,
        key="mood_rating",
    )
    stress_rating = st.number_input(
        "Stress rating (1-10)",
        min_value=1,
        max_value=10,
        value=4,
        step=1,
        key="stress_rating",
    )
    deep_work_minutes = st.number_input(
        "Deep work minutes",
        min_value=0,
        value=60,
        step=15,
        key="deep_work_minutes",
    )
    notes = st.text_area("Notes", key="notes")
    submitted = st.form_submit_button("Save daily check-in")

if submitted:
    payload = {
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
        save_daily_checkin(payload)
        st.success(f"Saved daily check-in for {checkin_date.isoformat()}.")
    except Exception as exc:
        st.error(
            "We couldn't save this daily check-in. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
