"""Minimal Postgres connection helpers for local MVP development."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv
import psycopg


load_dotenv()


@dataclass(frozen=True)
class PostgresConfig:
    """Container for environment-driven Postgres settings."""

    host: str
    port: int
    dbname: str
    user: str
    password: str


def get_db_config() -> PostgresConfig:
    """Read local Postgres settings from environment variables."""
    return PostgresConfig(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        dbname=os.getenv("PGDATABASE", "habit_focus_db"),
        user=os.getenv("PGUSER", "habit_user"),
        password=os.getenv("PGPASSWORD", "habit_pw"),
    )


def get_connection() -> psycopg.Connection:
    """Open a simple Postgres connection for future MVP database work."""
    config = get_db_config()
    return psycopg.connect(
        host=config.host,
        port=config.port,
        dbname=config.dbname,
        user=config.user,
        password=config.password,
    )
