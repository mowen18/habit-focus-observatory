"""Streamlit form rendering for the habit app."""

from datetime import date, time

import streamlit as st

from src.habit_repository import (
    load_caffeine_summary_values,
    load_daily_checkin_values,
    load_exercise_summary_values,
    replace_caffeine_summary,
    replace_exercise_summary,
    save_deep_work_minutes,
    save_morning_checkin,
)


MORNING_DEFAULTS = {
    "sleep_hours": 7.5,
    "sleep_quality": 7,
    "energy_rating": 7,
    "focus_rating": 7,
    "mood_rating": 7,
    "stress_rating": 4,
    "notes": "",
}
DEEP_WORK_DEFAULTS = {"deep_work_minutes": 60}
CAFFEINE_DEFAULTS = {
    "total_caffeine_mg": 0,
    "last_caffeine_time": time(14, 0),
}
EXERCISE_DEFAULTS = {
    "duration_minutes": 0,
    "intensity": "",
    "start_time": time(7, 0),
}


def _clean_text(value: str):
    """Normalize blank text inputs to None."""
    cleaned = value.strip()
    return cleaned or None


def _render_save_error(exc: Exception) -> None:
    """Show a friendly save error for this MVP app."""
    st.error(
        "We couldn't save this entry. "
        f"Please confirm Postgres is running and try again. Details: {exc}"
    )


def _sync_form_state(form_name: str, selected_date: date, values_by_key: dict) -> None:
    """Update widget state only when a section's selected date changes."""
    loaded_date_key = f"{form_name}_loaded_date"
    if st.session_state.get(loaded_date_key) == selected_date:
        return

    for key, value in values_by_key.items():
        st.session_state[key] = value
    st.session_state[loaded_date_key] = selected_date


def _value_or_default(values: dict, key: str, default):
    """Use saved values when present while keeping form defaults local."""
    value = values.get(key, default)
    return default if value is None else value


def render_morning_checkin_form(today: date) -> None:
    """Render the Today Morning Check-in form."""
    st.subheader("1. Today Morning Check-in")
    morning_checkin_date = st.date_input(
        "Check-in date",
        value=today,
        key="morning_checkin_date",
    )
    try:
        morning_saved_values = load_daily_checkin_values(morning_checkin_date)
    except Exception as exc:
        st.error(
            "We couldn't load the saved morning check-in values. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
        morning_saved_values = {}

    _sync_form_state(
        "morning_form",
        morning_checkin_date,
        {
            "morning_sleep_hours": _value_or_default(
                morning_saved_values,
                "sleep_hours",
                MORNING_DEFAULTS["sleep_hours"],
            ),
            "morning_sleep_quality": _value_or_default(
                morning_saved_values,
                "sleep_quality",
                MORNING_DEFAULTS["sleep_quality"],
            ),
            "morning_energy_rating": _value_or_default(
                morning_saved_values,
                "energy_rating",
                MORNING_DEFAULTS["energy_rating"],
            ),
            "morning_focus_rating": _value_or_default(
                morning_saved_values,
                "focus_rating",
                MORNING_DEFAULTS["focus_rating"],
            ),
            "morning_mood_rating": _value_or_default(
                morning_saved_values,
                "mood_rating",
                MORNING_DEFAULTS["mood_rating"],
            ),
            "morning_stress_rating": _value_or_default(
                morning_saved_values,
                "stress_rating",
                MORNING_DEFAULTS["stress_rating"],
            ),
            "morning_notes": morning_saved_values.get("notes", MORNING_DEFAULTS["notes"]),
        },
    )

    with st.form("today_morning_checkin_form"):
        morning_sleep_hours = st.number_input(
            "Sleep hours",
            min_value=0.0,
            max_value=24.0,
            step=0.25,
            key="morning_sleep_hours",
        )

        morning_rating_col_1, morning_rating_col_2, morning_rating_col_3 = st.columns(3)
        morning_sleep_quality = morning_rating_col_1.number_input(
            "Sleep quality (1-10)",
            min_value=1,
            max_value=10,
            step=1,
            key="morning_sleep_quality",
        )
        morning_energy_rating = morning_rating_col_2.number_input(
            "Energy rating (1-10)",
            min_value=1,
            max_value=10,
            step=1,
            key="morning_energy_rating",
        )
        morning_focus_rating = morning_rating_col_3.number_input(
            "Focus rating (1-10)",
            min_value=1,
            max_value=10,
            step=1,
            key="morning_focus_rating",
        )

        morning_rating_col_4, morning_rating_col_5 = st.columns(2)
        morning_mood_rating = morning_rating_col_4.number_input(
            "Mood rating (1-10)",
            min_value=1,
            max_value=10,
            step=1,
            key="morning_mood_rating",
        )
        morning_stress_rating = morning_rating_col_5.number_input(
            "Stress rating (1-10)",
            min_value=1,
            max_value=10,
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
            st.success(
                f"Saved today's morning check-in for {morning_checkin_date.isoformat()}."
            )
        except Exception as exc:
            _render_save_error(exc)


def render_deep_work_form(yesterday: date) -> None:
    """Render the Yesterday Deep Work form."""
    st.subheader("2. Yesterday Deep Work")
    deep_work_date = st.date_input(
        "Check-in date",
        value=yesterday,
        key="deep_work_date",
    )
    try:
        deep_work_saved_values = load_daily_checkin_values(deep_work_date)
    except Exception as exc:
        st.error(
            "We couldn't load the saved deep work values. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
        deep_work_saved_values = {}

    _sync_form_state(
        "deep_work_form",
        deep_work_date,
        {
            "deep_work_minutes": _value_or_default(
                deep_work_saved_values,
                "deep_work_minutes",
                DEEP_WORK_DEFAULTS["deep_work_minutes"],
            )
        },
    )

    with st.form("yesterday_deep_work_form"):
        deep_work_minutes = st.number_input(
            "Deep work minutes",
            min_value=0,
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


def render_caffeine_summary_form(yesterday: date) -> None:
    """Render the Yesterday Caffeine Summary form."""
    st.subheader("3. Yesterday Caffeine Summary")
    caffeine_checkin_date = st.date_input(
        "Check-in date",
        value=yesterday,
        key="caffeine_checkin_date",
    )
    try:
        caffeine_saved_values = load_caffeine_summary_values(caffeine_checkin_date)
    except Exception as exc:
        st.error(
            "We couldn't load the saved caffeine values. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
        caffeine_saved_values = {}

    _sync_form_state(
        "caffeine_form",
        caffeine_checkin_date,
        {
            "total_caffeine_mg": _value_or_default(
                caffeine_saved_values,
                "total_caffeine_mg",
                CAFFEINE_DEFAULTS["total_caffeine_mg"],
            ),
            "last_caffeine_time": _value_or_default(
                caffeine_saved_values,
                "last_caffeine_time",
                CAFFEINE_DEFAULTS["last_caffeine_time"],
            ),
        },
    )

    with st.form("yesterday_caffeine_form"):
        total_caffeine_mg = st.number_input(
            "Total caffeine mg",
            min_value=0,
            step=5,
            key="total_caffeine_mg",
        )
        last_caffeine_time = st.time_input(
            "Last caffeine time",
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
            st.success(f"Saved caffeine summary for {caffeine_checkin_date.isoformat()}.")
        except Exception as exc:
            _render_save_error(exc)


def render_exercise_form(yesterday: date) -> None:
    """Render the Yesterday Exercise form."""
    st.subheader("4. Yesterday Exercise")
    exercise_checkin_date = st.date_input(
        "Check-in date",
        value=yesterday,
        key="exercise_checkin_date",
    )
    try:
        exercise_saved_values = load_exercise_summary_values(exercise_checkin_date)
    except Exception as exc:
        st.error(
            "We couldn't load the saved exercise values. "
            f"Please confirm Postgres is running and try again. Details: {exc}"
        )
        exercise_saved_values = {}

    _sync_form_state(
        "exercise_form",
        exercise_checkin_date,
        {
            "exercise_duration_minutes": _value_or_default(
                exercise_saved_values,
                "duration_minutes",
                EXERCISE_DEFAULTS["duration_minutes"],
            ),
            "exercise_intensity": _value_or_default(
                exercise_saved_values,
                "intensity",
                EXERCISE_DEFAULTS["intensity"],
            ),
            "exercise_start_time": _value_or_default(
                exercise_saved_values,
                "start_time",
                EXERCISE_DEFAULTS["start_time"],
            ),
        },
    )

    with st.form("yesterday_exercise_form"):
        exercise_duration_minutes = st.number_input(
            "Duration minutes",
            min_value=0,
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
            st.success(f"Saved exercise for {exercise_checkin_date.isoformat()}.")
        except Exception as exc:
            _render_save_error(exc)
