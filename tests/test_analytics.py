"""Unit tests for pure pandas insight summaries."""

from pathlib import Path
import sys

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics import build_insight_summaries


def _find_summary(summaries, text):
    """Return the first summary containing text."""
    return next(summary for summary in summaries if text in summary)


def test_completeness_summary_appears():
    completeness_df = pd.DataFrame(
        {
            "completed_sections": [4, 4, 3],
            "expected_sections": [4, 4, 4],
            "has_checkin": [True, True, True],
            "has_deep_work_entry": [True, True, False],
            "has_caffeine_entry": [True, True, True],
            "has_exercise_entry": [True, True, True],
        }
    )

    summaries = build_insight_summaries(pd.DataFrame(), completeness_df)

    assert any(
        "2 of 3 days in this review window have all sections logged" in summary
        for summary in summaries
    )


def test_completeness_summary_identifies_missing_section():
    completeness_df = pd.DataFrame(
        {
            "completed_sections": [3, 3, 4, 3],
            "expected_sections": [4, 4, 4, 4],
            "has_checkin": [True, True, True, True],
            "has_deep_work_entry": [True, True, True, True],
            "has_caffeine_entry": [False, False, True, False],
            "has_exercise_entry": [True, True, True, True],
        }
    )

    summaries = build_insight_summaries(pd.DataFrame(), completeness_df)

    completeness_summary = _find_summary(summaries, "most commonly missing")
    assert "caffeine" in completeness_summary


def test_sleep_focus_comparison_appears_when_both_groups_have_enough_rows():
    analysis_df = pd.DataFrame(
        {
            "has_checkin": [True, True, True, True],
            "sleep_hours": [7.0, 8.0, 6.0, 5.5],
            "focus_rating": [8, 8, 5, 7],
        }
    )

    summaries = build_insight_summaries(
        analysis_df,
        pd.DataFrame(),
        min_days=2,
    )

    sleep_summary = _find_summary(summaries, "Average focus")
    assert "2.0 points higher on 7+ hour sleep days" in sleep_summary
    assert "based on 2 vs 2 logged days" in sleep_summary


def test_sleep_focus_sufficiency_message_appears_when_not_enough_rows():
    analysis_df = pd.DataFrame(
        {
            "has_checkin": [True, True, True],
            "sleep_hours": [7.0, 8.0, 6.0],
            "focus_rating": [8, 8, 5],
        }
    )

    summaries = build_insight_summaries(
        analysis_df,
        pd.DataFrame(),
        min_days=2,
    )

    assert any(
        "Not enough logged sleep/focus data yet" in summary
        for summary in summaries
    )


def test_caffeine_insight_ignores_unlogged_caffeine_rows():
    analysis_df = pd.DataFrame(
        {
            "prior_day_has_caffeine_entry": [
                True,
                True,
                True,
                False,
                True,
                True,
                True,
            ],
            "prior_day_total_caffeine_mg": [120, 90, 150, 0, 0, 0, 0],
            "sleep_quality": [6, 6, 6, 10, 8, 8, 8],
        }
    )

    summaries = build_insight_summaries(
        analysis_df,
        pd.DataFrame(),
        min_days=3,
    )

    caffeine_summary = _find_summary(summaries, "sleep quality averaged")
    assert "6.0 after caffeine days versus 8.0 after no-caffeine days" in caffeine_summary
    assert "based on 3 vs 3 logged days" in caffeine_summary


def test_caffeine_insight_treats_logged_zero_as_no_caffeine_day():
    analysis_df = pd.DataFrame(
        {
            "prior_day_has_caffeine_entry": [True, True, True, True],
            "prior_day_total_caffeine_mg": [100, 120, 0, 0],
            "sleep_quality": [6, 7, 8, 9],
        }
    )

    summaries = build_insight_summaries(
        analysis_df,
        pd.DataFrame(),
        min_days=2,
    )

    caffeine_summary = _find_summary(summaries, "sleep quality averaged")
    assert "6.5 after caffeine days versus 8.5 after no-caffeine days" in caffeine_summary
    assert "based on 2 vs 2 logged days" in caffeine_summary


def test_exercise_insight_includes_sample_sizes():
    analysis_df = pd.DataFrame(
        {
            "prior_day_has_exercise_entry": [True, True, True, True, True],
            "prior_day_total_exercise_minutes": [30, 45, 0, 0, 0],
            "energy_rating": [8, 6, 5, 6, 7],
        }
    )

    summaries = build_insight_summaries(
        analysis_df,
        pd.DataFrame(),
        min_days=2,
    )

    exercise_summary = _find_summary(summaries, "energy averaged")
    assert "based on 2 vs 3 logged days" in exercise_summary
