"""Load a deterministic synthetic demo dataset into local Postgres."""

from dataclasses import dataclass
from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.db import get_connection  # noqa: E402


DEMO_START_DATE = date(2026, 1, 1)
DEMO_END_DATE = date(2026, 1, 30)


@dataclass(frozen=True)
class DemoDay:
    """One synthetic day with explicit logged-vs-missing section semantics."""

    checkin_date: date
    sleep_hours: Optional[Decimal]
    sleep_quality: Optional[int]
    energy_rating: Optional[int]
    focus_rating: Optional[int]
    mood_rating: Optional[int]
    stress_rating: Optional[int]
    deep_work_logged: bool
    deep_work_minutes: Optional[int]
    caffeine_logged: bool
    caffeine_mg: Optional[int]
    last_caffeine_time: Optional[time]
    exercise_logged: bool
    exercise_minutes: Optional[int]
    exercise_intensity: Optional[str]
    exercise_start_time: Optional[time]
    notes: Optional[str]


def _decimal_hours(hours: float) -> Decimal:
    """Return a two-decimal Decimal for NUMERIC(4,2) sleep hours."""
    return Decimal(f"{hours:.2f}")


def build_demo_days() -> list:
    """Build 30 fixed synthetic days for local demos and analytics checks."""
    strong_sleep_days = {
        1,
        2,
        3,
        5,
        6,
        8,
        9,
        10,
        12,
        13,
        15,
        16,
        17,
        20,
        22,
        23,
        24,
        27,
        29,
        30,
    }
    missing_morning_days = {11, 21, 28}
    zero_caffeine_days = {4, 9, 15, 22, 29}
    missing_caffeine_days = {7, 14, 21, 28}
    zero_exercise_days = {3, 10, 17, 24, 30}
    missing_exercise_days = {6, 13, 20, 27}
    zero_deep_work_days = {5, 12, 19, 26}
    missing_deep_work_days = {8, 16, 21, 28}

    demo_days = []
    for offset in range((DEMO_END_DATE - DEMO_START_DATE).days + 1):
        day_number = offset + 1
        checkin_date = DEMO_START_DATE + timedelta(days=offset)
        has_strong_sleep = day_number in strong_sleep_days

        if day_number in missing_morning_days:
            sleep_hours = None
            sleep_quality = None
            energy_rating = None
            focus_rating = None
            mood_rating = None
            stress_rating = None
            notes = None
        elif has_strong_sleep:
            sleep_hours = _decimal_hours(7.1 + ((day_number % 4) * 0.25))
            sleep_quality = 7 + (day_number % 3)
            energy_rating = 7 + (day_number % 3)
            focus_rating = 7 + ((day_number + 1) % 3)
            mood_rating = 7 + (day_number % 2)
            stress_rating = 3 + (day_number % 2)
            notes = "Synthetic demo: rested morning with stronger focus."
        else:
            sleep_hours = _decimal_hours(5.8 + ((day_number % 4) * 0.22))
            sleep_quality = 4 + (day_number % 3)
            energy_rating = 4 + ((day_number + 1) % 3)
            focus_rating = 4 + (day_number % 3)
            mood_rating = 5 + (day_number % 2)
            stress_rating = 6 + (day_number % 2)
            notes = "Synthetic demo: short sleep with lighter focus."

        if day_number in missing_deep_work_days:
            deep_work_logged = False
            deep_work_minutes = None
        elif day_number in zero_deep_work_days:
            deep_work_logged = True
            deep_work_minutes = 0
        else:
            deep_work_logged = True
            if has_strong_sleep:
                deep_work_minutes = 95 + ((day_number % 5) * 20)
            else:
                deep_work_minutes = 25 + ((day_number % 4) * 15)

        if day_number in missing_caffeine_days:
            caffeine_logged = False
            caffeine_mg = None
            last_caffeine_time = None
        elif day_number in zero_caffeine_days:
            caffeine_logged = True
            caffeine_mg = 0
            last_caffeine_time = None
        else:
            caffeine_logged = True
            caffeine_mg = 80 + ((day_number % 4) * 35)
            last_caffeine_time = time(9 + (day_number % 3), 15)

        if day_number in missing_exercise_days:
            exercise_logged = False
            exercise_minutes = None
            exercise_intensity = None
            exercise_start_time = None
        elif day_number in zero_exercise_days:
            exercise_logged = True
            exercise_minutes = 0
            exercise_intensity = None
            exercise_start_time = None
        else:
            exercise_logged = True
            exercise_minutes = 20 + ((day_number % 5) * 10)
            exercise_intensity = "high" if day_number in {2, 9, 18, 23} else "moderate"
            exercise_start_time = time(7 + (day_number % 3), 0)

        demo_days.append(
            DemoDay(
                checkin_date=checkin_date,
                sleep_hours=sleep_hours,
                sleep_quality=sleep_quality,
                energy_rating=energy_rating,
                focus_rating=focus_rating,
                mood_rating=mood_rating,
                stress_rating=stress_rating,
                deep_work_logged=deep_work_logged,
                deep_work_minutes=deep_work_minutes,
                caffeine_logged=caffeine_logged,
                caffeine_mg=caffeine_mg,
                last_caffeine_time=last_caffeine_time,
                exercise_logged=exercise_logged,
                exercise_minutes=exercise_minutes,
                exercise_intensity=exercise_intensity,
                exercise_start_time=exercise_start_time,
                notes=notes,
            )
        )

    return demo_days


def _delete_existing_demo_rows(cursor) -> None:
    """Delete only rows inside the fixed demo date range."""
    cursor.execute(
        """
        DELETE FROM caffeine_log
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    cursor.execute(
        """
        DELETE FROM exercise_log
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    cursor.execute(
        """
        DELETE FROM daily_checkin
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )


def _insert_demo_day(cursor, demo_day: DemoDay) -> None:
    """Insert one daily_checkin row and any positive child summary rows."""
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
            deep_work_logged,
            caffeine_logged,
            exercise_logged,
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
            %(deep_work_logged)s,
            %(caffeine_logged)s,
            %(exercise_logged)s,
            %(notes)s
        )
        """,
        demo_day.__dict__,
    )

    if demo_day.caffeine_logged and demo_day.caffeine_mg and demo_day.caffeine_mg > 0:
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
            (
                demo_day.checkin_date,
                demo_day.last_caffeine_time,
                "Synthetic coffee",
                demo_day.caffeine_mg,
            ),
        )

    if (
        demo_day.exercise_logged
        and demo_day.exercise_minutes
        and demo_day.exercise_minutes > 0
    ):
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
            (
                demo_day.checkin_date,
                "Synthetic workout",
                demo_day.exercise_minutes,
                demo_day.exercise_intensity,
                demo_day.exercise_start_time,
            ),
        )


def _load_summary(cursor) -> dict:
    """Return inserted row counts and completeness details for the demo range."""
    cursor.execute(
        """
        SELECT COUNT(*), MIN(checkin_date), MAX(checkin_date)
        FROM daily_checkin
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    daily_count, min_date, max_date = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM caffeine_log
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    caffeine_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM exercise_log
        WHERE checkin_date BETWEEN %s AND %s
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    exercise_count = cursor.fetchone()[0]

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM daily_completeness_vw
        WHERE checkin_date BETWEEN %s AND %s
            AND completed_sections = expected_sections
        """,
        (DEMO_START_DATE, DEMO_END_DATE),
    )
    full_data_days = cursor.fetchone()[0]

    return {
        "daily_checkin": daily_count,
        "caffeine_log": caffeine_count,
        "exercise_log": exercise_count,
        "full_data_days": full_data_days,
        "min_date": min_date,
        "max_date": max_date,
    }


def load_demo_data() -> dict:
    """Replace the fixed demo date range with deterministic synthetic rows."""
    demo_days = build_demo_days()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            _delete_existing_demo_rows(cursor)
            for demo_day in demo_days:
                _insert_demo_day(cursor, demo_day)
            summary = _load_summary(cursor)

    return summary


def main() -> None:
    """Load the demo dataset and print a compact verification summary."""
    summary = load_demo_data()
    print("Loaded deterministic synthetic demo data")
    print(f"daily_checkin rows inserted: {summary['daily_checkin']}")
    print(f"caffeine_log rows inserted: {summary['caffeine_log']}")
    print(f"exercise_log rows inserted: {summary['exercise_log']}")
    print(f"full data days from daily_completeness_vw: {summary['full_data_days']}")
    print(f"demo date range loaded: {summary['min_date']} to {summary['max_date']}")


if __name__ == "__main__":
    main()
