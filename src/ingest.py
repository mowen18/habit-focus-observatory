"""Minimal CSV ingestion for loading sample data into Postgres."""

import csv
from decimal import Decimal
from datetime import date, time
from pathlib import Path

try:
    from src.db import get_connection
except ImportError:  # pragma: no cover - supports direct script execution
    from db import get_connection


DEFAULT_DAILY_CSV_PATH = Path("data/sample_logs.csv")
DEFAULT_CAFFEINE_CSV_PATH = Path("data/sample_caffeine_log.csv")
DEFAULT_EXERCISE_CSV_PATH = Path("data/sample_exercise_log.csv")


def _read_csv_rows(csv_path: Path):
    """Return CSV rows as dictionaries for a given path."""
    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _to_optional_int(value: str):
    """Convert a CSV value to int, or None when blank."""
    cleaned = value.strip()
    return int(cleaned) if cleaned else None


def _to_optional_decimal(value: str):
    """Convert a CSV value to Decimal, or None when blank."""
    cleaned = value.strip()
    return Decimal(cleaned) if cleaned else None


def _to_optional_text(value: str):
    """Convert a CSV value to stripped text, or None when blank."""
    cleaned = value.strip()
    return cleaned or None


def _upsert_daily_checkins(cursor, rows) -> int:
    """Insert or update sample daily check-ins."""
    for row in rows:
        payload = {
            "checkin_date": date.fromisoformat(row["check_in_date"]),
            "sleep_hours": _to_optional_decimal(row["sleep_hours"]),
            "sleep_quality": _to_optional_int(row["sleep_quality"]),
            "mood_rating": _to_optional_int(row["mood_score"]),
            "stress_rating": _to_optional_int(row["stress_score"]),
            "deep_work_minutes": _to_optional_int(row["deep_work_minutes"]),
            "focus_rating": _to_optional_int(row["focus_score"]),
            "energy_rating": _to_optional_int(row["energy_score"]),
            "notes": _to_optional_text(row["notes"]),
        }

        cursor.execute(
            """
            INSERT INTO daily_checkin (
                checkin_date,
                sleep_hours,
                sleep_quality,
                mood_rating,
                stress_rating,
                deep_work_minutes,
                focus_rating,
                energy_rating,
                notes
            )
            VALUES (
                %(checkin_date)s,
                %(sleep_hours)s,
                %(sleep_quality)s,
                %(mood_rating)s,
                %(stress_rating)s,
                %(deep_work_minutes)s,
                %(focus_rating)s,
                %(energy_rating)s,
                %(notes)s
            )
            ON CONFLICT (checkin_date) DO UPDATE
            SET
                sleep_hours = EXCLUDED.sleep_hours,
                sleep_quality = EXCLUDED.sleep_quality,
                mood_rating = EXCLUDED.mood_rating,
                stress_rating = EXCLUDED.stress_rating,
                deep_work_minutes = EXCLUDED.deep_work_minutes,
                focus_rating = EXCLUDED.focus_rating,
                energy_rating = EXCLUDED.energy_rating,
                notes = EXCLUDED.notes
            """,
            payload,
        )

    return len(rows)


def _replace_caffeine_logs(cursor, rows) -> int:
    """Refresh sample caffeine events for the dates included in the CSV."""
    checkin_dates = sorted({date.fromisoformat(row["check_in_date"]) for row in rows})

    if checkin_dates:
        cursor.execute(
            "DELETE FROM caffeine_log WHERE checkin_date = ANY(%s)",
            (checkin_dates,),
        )

    for row in rows:
        payload = {
            "checkin_date": date.fromisoformat(row["check_in_date"]),
            "intake_time": time.fromisoformat(row["intake_time"]),
            "source": _to_optional_text(row["source"]),
            "caffeine_mg": int(row["caffeine_mg"]),
        }

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
            payload,
        )

    return len(rows)


def _replace_exercise_logs(cursor, rows) -> int:
    """Refresh sample exercise sessions for the dates included in the CSV."""
    checkin_dates = sorted({date.fromisoformat(row["check_in_date"]) for row in rows})

    if checkin_dates:
        cursor.execute(
            "DELETE FROM exercise_log WHERE checkin_date = ANY(%s)",
            (checkin_dates,),
        )

    for row in rows:
        payload = {
            "checkin_date": date.fromisoformat(row["check_in_date"]),
            "exercise_type": row["exercise_type"].strip(),
            "duration_minutes": int(row["duration_minutes"]),
            "intensity": _to_optional_text(row["intensity"]),
            "start_time": time.fromisoformat(row["start_time"]) if row["start_time"].strip() else None,
        }

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
            payload,
        )

    return len(rows)


def ingest_sample_data(
    daily_csv_path: Path = DEFAULT_DAILY_CSV_PATH,
    caffeine_csv_path: Path = DEFAULT_CAFFEINE_CSV_PATH,
    exercise_csv_path: Path = DEFAULT_EXERCISE_CSV_PATH,
):
    """Load sample daily check-ins, caffeine events, and exercise sessions."""
    daily_rows = _read_csv_rows(daily_csv_path)
    caffeine_rows = _read_csv_rows(caffeine_csv_path)
    exercise_rows = _read_csv_rows(exercise_csv_path)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            counts = {
                "daily_checkin": _upsert_daily_checkins(cursor, daily_rows),
                "caffeine_log": _replace_caffeine_logs(cursor, caffeine_rows),
                "exercise_log": _replace_exercise_logs(cursor, exercise_rows),
            }

    return counts


def main() -> None:
    """Run the sample ingestion path using the default CSV files."""
    counts = ingest_sample_data()
    print(
        "Loaded sample data: "
        f"{counts['daily_checkin']} daily_checkin rows, "
        f"{counts['caffeine_log']} caffeine_log rows, "
        f"{counts['exercise_log']} exercise_log rows"
    )


if __name__ == "__main__":
    main()
