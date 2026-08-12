import os
from contextlib import contextmanager

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

NEON_DB_URL = os.getenv("NEON_DB_URL")


@contextmanager
def _get_conn():
    # connect_timeout bounds the TCP/TLS handshake; statement_timeout bounds
    # any single query once connected -- psycopg2.connect() has no default
    # for either, so a stalled Neon cold-start or a stuck query hangs forever
    # with nothing to catch it (same class of bug as the earlier DNS hang in
    # scraping_helper.py, just on the DB side).
    conn = psycopg2.connect(
        NEON_DB_URL,
        connect_timeout=15,
        options="-c statement_timeout=120000",
    )
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _to_python(v):
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    if isinstance(v, pd.Timestamp):
        return v.to_pydatetime()
    return v


def read_table(table_name: str, topic: str | None = None) -> pd.DataFrame:
    """Read a table as DataFrame. Optional topic filter for news_articles / news_sentiment."""
    safe = table_name.replace('"', "")
    sql = f'SELECT * FROM "{safe}"'
    params: list = []
    if topic is not None:
        sql += " WHERE topic = %s"
        params.append(topic)
    sql += " ORDER BY id"
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or None)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


def upsert_df(table_name: str, df: pd.DataFrame, conflict_cols: list[str]) -> int:
    """Upsert DataFrame rows via ON CONFLICT DO UPDATE. Returns row count."""
    if df.empty:
        return 0

    cols         = list(df.columns)
    quoted_cols  = ", ".join(f'"{c}"' for c in cols)
    conflict_str = ", ".join(f'"{c}"' for c in conflict_cols)
    update_cols  = [c for c in cols if c not in conflict_cols]

    if update_cols:
        update_set = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
        on_conflict = f"ON CONFLICT ({conflict_str}) DO UPDATE SET {update_set}"
    else:
        on_conflict = f"ON CONFLICT ({conflict_str}) DO NOTHING"

    safe = table_name.replace('"', "")
    # VALUES %s is a single placeholder execute_values expands into
    # (row1), (row2), ... -- one INSERT per page instead of psycopg2's
    # default executemany, which round-trips to the DB once per row and
    # made saving tens of thousands of scraped rows take tens of minutes.
    sql = (
        f'INSERT INTO "{safe}" ({quoted_cols}) '
        f"VALUES %s "
        f"{on_conflict}"
    )

    rows = [
        tuple(_to_python(v) for v in row)
        for row in df.itertuples(index=False, name=None)
    ]

    with _get_conn() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, rows)

    return len(rows)


def create_table_if_needed(
    table_name: str,
    df: pd.DataFrame,
    conflict_cols: list[str],
) -> None:
    """
    Create table from DataFrame schema if it does not exist yet.
    Also adds any missing columns to an existing table (for dynamic schemas like WTE).
    Column types are inferred from pandas dtypes.
    """
    safe = table_name.replace('"', "")

    def _pg_type(dtype) -> str:
        if pd.api.types.is_integer_dtype(dtype):
            return "BIGINT"
        if pd.api.types.is_float_dtype(dtype):
            return "DOUBLE PRECISION"
        if pd.api.types.is_datetime64_any_dtype(dtype):
            return "TIMESTAMP"
        return "TEXT"

    col_defs = ", ".join(
        f'"{col}" {_pg_type(df[col].dtype)}'
        for col in df.columns
    )
    conflict_quoted = ", ".join(f'"{c}"' for c in conflict_cols)
    unique_def = f", UNIQUE ({conflict_quoted})"

    create_sql = (
        f'CREATE TABLE IF NOT EXISTS "{safe}" '
        f'(id SERIAL PRIMARY KEY, {col_defs}{unique_def})'
    )

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            # Add missing columns for existing tables
            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = %s",
                (safe,),
            )
            existing_cols = {row[0] for row in cur.fetchall()}
            for col in df.columns:
                if col not in existing_cols:
                    cur.execute(
                        f'ALTER TABLE "{safe}" ADD COLUMN IF NOT EXISTS "{col}" {_pg_type(df[col].dtype)}'
                    )
