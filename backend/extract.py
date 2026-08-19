"""
extract.py
----------
Handles the Extract step of the ETL pipeline.
Reads a CSV file and performs basic file-level validation.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def extract_csv(file_path: str, expected_columns: list) -> pd.DataFrame:
    """
    Read a CSV file into a Pandas DataFrame.

    Checks performed:
    1. File exists on disk
    2. File is readable
    3. File is not empty (has at least one data row)
    4. All expected columns are present

    Args:
        file_path: Path to the CSV file.
        expected_columns: List of column names that must exist.

    Returns:
        A Pandas DataFrame with the CSV data.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file is empty or missing required columns.
        Exception: For any other read error.
    """
    logger.info("Extraction started — file: %s", file_path)

    # --- Check 1: File exists ---
    if not os.path.exists(file_path):
        msg = f"Input file not found: {file_path}"
        logger.error(msg)
        raise FileNotFoundError(msg)

    # --- Check 2: Read the file ---
    try:
        df = pd.read_csv(file_path)
        logger.info("File read successfully. Shape: %s", df.shape)
    except Exception as e:
        msg = f"Failed to read CSV file: {e}"
        logger.error(msg)
        raise Exception(msg)

    # --- Check 3: File is not empty ---
    if df.empty or len(df) == 0:
        msg = "Input file contains zero records."
        logger.warning(msg)
        raise ValueError(msg)

    # --- Check 4: Expected columns exist ---
    actual_columns = list(df.columns)
    missing_cols = [col for col in expected_columns if col not in actual_columns]

    if missing_cols:
        msg = f"Missing required columns: {missing_cols}. Expected: {expected_columns}, Got: {actual_columns}"
        logger.error(msg)
        raise ValueError(msg)

    logger.info("Extraction successful. Records: %d", len(df))
    return df
