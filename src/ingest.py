"""Minimal CSV ingestion for loading daily check-ins into Postgres."""

import csv
from datetime import date
from pathlib import Path
import sys

try:
    from src.db import get_connection
except ImportError:  # pragma: no cover - supports direct script execution
    from db import get_connection


DEFAULT_CSV_PATH = Path("data/sample_logs.csv")


def _to_optional_int(value: str):
    """Convert a CSV value to int, or None when blank."""
    cleaned = value.strip()
    return int(cleaned) if cleaned else None


def ingest_csv(csv_path: Path = DEFAULT_CSV_PATH) -> int:
    """Load daily check-in rows from CSV into the daily_checkin table."""
    rows_loaded = 0

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)

        with get_connection() as connection:
            with connection.cursor() as cursor:
                for row in reader:
                    payload = {
                        "checkin_date": date.fromisoformat(row["check_in_date"]),
                        "focus_rating": _to_optional_int(row["focus_score"]),
                        "energy_rating": _to_optional_int(row["energy_score"]),
                        "notes": row["notes"].strip() or None,
                    }

                    cursor.execute(
                        """
                        INSERT INTO daily_checkin (
                            checkin_date,
                            focus_rating,
                            energy_rating,
                            notes
                        )
                        VALUES (
                            %(checkin_date)s,
                            %(focus_rating)s,
                            %(energy_rating)s,
                            %(notes)s
                        )
                        ON CONFLICT (checkin_date) DO UPDATE
                        SET
                            focus_rating = EXCLUDED.focus_rating,
                            energy_rating = EXCLUDED.energy_rating,
                            notes = EXCLUDED.notes
                        """,
                        payload,
                    )
                    rows_loaded += 1

    return rows_loaded


def main() -> None:
    """Run the MVP CSV ingestion path with an optional file override."""
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV_PATH
    rows_loaded = ingest_csv(csv_path)
    print(f"Loaded {rows_loaded} daily check-in rows from {csv_path}")


if __name__ == "__main__":
    main()
