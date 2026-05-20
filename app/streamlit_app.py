"""Streamlit app for a simple morning habit and focus workflow."""

from datetime import date, timedelta
from pathlib import Path
import sys

import streamlit as st


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.forms import (  # noqa: E402
    render_caffeine_summary_form,
    render_deep_work_form,
    render_exercise_form,
    render_morning_checkin_form,
)
from app.review import render_recent_review  # noqa: E402


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)


def main() -> None:
    """Render the single-page Streamlit app."""
    st.set_page_config(page_title="Habit Focus Observatory", layout="centered")
    st.title("Habit Focus Observatory")
    st.caption("Simple morning workflow for the MVP.")
    st.write(
        "Use the forms below to record today's check-in and yesterday's supporting summaries."
    )

    render_morning_checkin_form(TODAY)
    render_deep_work_form(YESTERDAY)
    render_caffeine_summary_form(YESTERDAY)
    render_exercise_form(YESTERDAY)
    render_recent_review()


main()
