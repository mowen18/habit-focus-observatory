"""Unit tests for review-window date resolution."""

from datetime import date
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.review import (  # noqa: E402
    DEMO_WINDOW_LABEL,
    RECENT_WINDOW_LABEL,
    resolve_review_window,
)


def test_recent_review_window_returns_last_14_calendar_days():
    today = date(2026, 6, 8)

    start_date, end_date, caption = resolve_review_window(
        RECENT_WINDOW_LABEL,
        today=today,
    )

    assert start_date == date(2026, 5, 26)
    assert end_date == today
    assert caption == "Showing last 14 calendar days: 2026-05-26 to 2026-06-08."


def test_demo_review_window_returns_fixed_demo_range():
    start_date, end_date, caption = resolve_review_window(
        DEMO_WINDOW_LABEL,
        today=date(2026, 6, 8),
    )

    assert start_date == date(2026, 1, 1)
    assert end_date == date(2026, 1, 30)
    assert caption == (
        "Showing deterministic synthetic demo data from 2026-01-01 to 2026-01-30."
    )
