"""Ingestion placeholders for loading raw habit log data into the datastore."""

from pathlib import Path


def ingest_csv(csv_path: Path) -> None:
    """Placeholder for CSV ingestion logic."""
    raise NotImplementedError(f"Ingestion is not implemented yet for: {csv_path}")
