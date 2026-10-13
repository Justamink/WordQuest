"""Shared database helpers for the WordQuest Streamlit app."""
import os

import psycopg
from psycopg import errors
from psycopg.rows import dict_row
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    """Open a new PostgreSQL connection (rows come back as dicts).

    Use as a context manager: the transaction commits on success, rolls back
    on error, and the connection is closed afterwards.
    """
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "wordquest"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


def query(sql, params=None):
    """Run a SELECT and return a list of dict rows."""
    with get_conn() as conn:
        return conn.execute(sql, params).fetchall()


def execute(sql, params=None):
    """Run an INSERT/UPDATE/DELETE.

    Returns the rows if the statement has a RETURNING clause, otherwise the
    number of rows affected.
    """
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        if cur.description:
            return cur.fetchall()
        return cur.rowcount


def friendly_error(e):
    """Turn a database exception into a readable message for the user."""
    if isinstance(e, errors.UniqueViolation):
        return "That record already exists, so it can't be added again."
    if isinstance(e, errors.ForeignKeyViolation):
        return (
            "This action conflicts with related data: either something it "
            "refers to doesn't exist, or other records still depend on it."
        )
    if isinstance(e, errors.CheckViolation):
        return "One of the values isn't allowed by the database rules. Please check your input."
    if isinstance(e, errors.NotNullViolation):
        return "A required field was left empty."
    if isinstance(e, psycopg.OperationalError):
        return "Could not connect to the database. Check that PostgreSQL is running and your .env settings are correct."
    if isinstance(e, psycopg.errors.UndefinedTable) or isinstance(e, psycopg.errors.UndefinedColumn):
        return f"The query doesn't match your schema (table/column name problem): {e}"
    return f"Something went wrong: {e}"