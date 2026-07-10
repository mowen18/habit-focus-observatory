"""PostgreSQL regression tests for calendar-aware fallback analytics."""

from decimal import Decimal
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from psycopg import sql

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402


SCHEMA_SQL = (PROJECT_ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")
VIEWS_SQL = (PROJECT_ROOT / "sql" / "views.sql").read_text(encoding="utf-8")
ANALYSIS_SQL = (PROJECT_ROOT / "sql" / "analysis_queries.sql").read_text(
    encoding="utf-8"
)
NEXT_DAY_QUERY_START = (
    "-- Shows next-day focus following days that did or did not include "
    "high-intensity exercise."
)
NEXT_DAY_QUERY_END = (
    "-- Compares exercise volume on high-focus days versus other days."
)


def _extract_next_day_query() -> str:
    """Return the executable next-day statement from the analysis SQL file."""
    query_section = ANALYSIS_SQL.split(NEXT_DAY_QUERY_START, maxsplit=1)[1]
    return query_section.split(NEXT_DAY_QUERY_END, maxsplit=1)[0].strip()


NEXT_DAY_QUERY = _extract_next_day_query()


@pytest.fixture
def fallback_connection():
    """Build fallback tables and views in a transaction-scoped schema."""
    connection = get_connection()
    schema_name = f"temporal_test_{uuid4().hex}"

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name))
            )
            cursor.execute(
                sql.SQL("SET LOCAL search_path TO {}").format(
                    sql.Identifier(schema_name)
                )
            )
            cursor.execute(SCHEMA_SQL)
            cursor.execute(VIEWS_SQL)
        yield connection
    finally:
        connection.rollback()
        connection.close()


def _insert_checkins(connection, rows) -> None:
    """Insert sparse daily check-in fixture rows."""
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO daily_checkin (
                checkin_date,
                sleep_hours,
                focus_rating,
                exercise_logged
            )
            VALUES (%s, %s, %s, %s)
            """,
            rows,
        )


def test_fallback_prior_day_sleep_is_null_across_gap(fallback_connection):
    _insert_checkins(
        fallback_connection,
        [
            ("2026-01-08", Decimal("7.0"), None, False),
            ("2026-01-10", None, None, False),
        ],
    )

    with fallback_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT prior_day_sleep_hours
            FROM daily_metrics_vw
            WHERE checkin_date = DATE '2026-01-10'
            """
        )
        assert cursor.fetchone()[0] is None


def test_fallback_prior_day_sleep_uses_exact_previous_date(fallback_connection):
    _insert_checkins(
        fallback_connection,
        [
            ("2026-01-09", Decimal("7.5"), None, False),
            ("2026-01-10", None, None, False),
        ],
    )

    with fallback_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT prior_day_sleep_hours
            FROM daily_metrics_vw
            WHERE checkin_date = DATE '2026-01-10'
            """
        )
        assert cursor.fetchone()[0] == Decimal("7.5")


def test_fallback_focus_7d_avg_uses_calendar_range(fallback_connection):
    _insert_checkins(
        fallback_connection,
        [
            ("2026-01-01", None, 4, False),
            ("2026-01-08", None, 8, False),
            ("2026-01-10", None, 10, False),
        ],
    )

    with fallback_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT focus_7d_avg
            FROM daily_metrics_vw
            WHERE checkin_date = DATE '2026-01-10'
            """
        )
        assert cursor.fetchone()[0] == Decimal("9.0")


def test_next_day_analysis_requires_exact_date_and_logged_exercise(
    fallback_connection,
):
    _insert_checkins(
        fallback_connection,
        [
            ("2026-01-08", None, None, True),
            ("2026-01-10", None, 10, True),
            ("2026-01-11", None, 6, False),
            ("2026-01-12", None, 7, False),
        ],
    )
    with fallback_connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO exercise_log (
                checkin_date,
                exercise_type,
                duration_minutes,
                intensity
            )
            VALUES (DATE '2026-01-08', 'Intervals', 30, 'high')
            """
        )
        cursor.execute(NEXT_DAY_QUERY)
        assert cursor.fetchall() == [(0, 1, Decimal("6.00"))]
