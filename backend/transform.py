"""
transform.py
------------
Data transformation step of the ETL pipeline.
Performs simple cleaning and standardisation.
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)


def transform_customers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardise customer data.

    Transformations:
    - Strip leading/trailing whitespace from all string columns
    - Title-case city names  (e.g. 'bangalore' -> 'Bangalore')
    - Title-case names       (e.g. 'rahul'     -> 'Rahul')
    - Lowercase emails       (e.g. 'RAHUL@GMAIL.COM' -> 'rahul@gmail.com')
    - Ensure customer_id is an integer

    Args:
        df: Raw customer DataFrame from extraction.

    Returns:
        Cleaned DataFrame.
    """
    logger.info("Transforming customer data (%d records)...", len(df))

    # Work on a copy so we don't mutate the original
    df = df.copy()

    # Strip whitespace from all string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    # Standardise text fields
    if "name" in df.columns:
        df["name"] = df["name"].str.title()

    if "email" in df.columns:
        df["email"] = df["email"].str.lower()

    if "city" in df.columns:
        df["city"] = df["city"].str.title()

    # Ensure numeric ID
    if "customer_id" in df.columns:
        df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce")

    logger.info("Customer transformation complete.")
    return df


def transform_orders(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardise order data.

    Transformations:
    - Strip leading/trailing whitespace from all string columns
    - Uppercase status values (e.g. 'completed' -> 'COMPLETED')
    - Parse order_date to standard YYYY-MM-DD string
    - Cast amount to float, coerce non-numeric to NaN
    - Ensure order_id and customer_id are integers

    Args:
        df: Raw orders DataFrame from extraction.

    Returns:
        Cleaned DataFrame.
    """
    logger.info("Transforming order data (%d records)...", len(df))

    df = df.copy()

    # Strip whitespace from string columns
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()

    # Standardise status to uppercase
    if "status" in df.columns:
        df["status"] = df["status"].str.upper()

    # Parse and standardise date format
    if "order_date" in df.columns:
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    # Ensure amount is numeric
    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    # Ensure integer IDs
    for id_col in ["order_id", "customer_id"]:
        if id_col in df.columns:
            df[id_col] = pd.to_numeric(df[id_col], errors="coerce")

    logger.info("Order transformation complete.")
    return df
