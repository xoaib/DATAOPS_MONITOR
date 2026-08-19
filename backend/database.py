"""
database.py
-----------
Handles SQLite connection and database initialisation.
Reads schema.sql to create all tables on first run.
"""

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

# Path to the SQLite database file (created automatically)
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "dataops.db")

# Path to the SQL schema file
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "sql", "schema.sql")


def get_db() -> sqlite3.Connection:
    """
    Return a new SQLite connection with row_factory set
    so results come back as dictionary-like objects.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """
    Read schema.sql and execute it against the database.
    Creates tables if they do not already exist.
    Called once when the FastAPI app starts.
    """
    logger.info("Initialising database at: %s", os.path.abspath(DB_PATH))

    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()

    conn = get_db()
    try:
        conn.executescript(schema_sql)
        conn.commit()
        logger.info("Database initialised successfully.")
    except Exception as e:
        logger.error("Database initialisation failed: %s", e)
        raise
    finally:
        conn.close()
