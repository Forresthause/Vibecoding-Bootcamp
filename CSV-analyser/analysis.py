"""CSV loading and statistics, independent of the Streamlit interface."""

from io import BytesIO
from math import isfinite

import pandas as pd


class CSVValidationError(ValueError):
    """An upload cannot be used; the message can be shown to the user."""


def parse_csv(file_bytes: bytes) -> pd.DataFrame:
    """Read a UTF-8, comma-separated CSV whose first row contains headers.

    Preserve values as strings for later numeric classification. Only empty or
    whitespace-only cells become missing values; text such as 'NA' is preserved.
    Pandas handles CSV quoting and blank lines. This deliberately does not try
    to detect other delimiters, missing headers, or every malformed CSV shape.
    """
    try:
        data = pd.read_csv(
            BytesIO(file_bytes),
            encoding="utf-8-sig",
            sep=",",
            header=0,
            dtype=str,
            keep_default_na=False,
        )
    except UnicodeDecodeError as exc:
        raise CSVValidationError(
            "Could not read this file. Export it as a UTF-8 CSV and try again."
        ) from exc
    except pd.errors.EmptyDataError as exc:
        raise CSVValidationError(
            "No data found. Upload a CSV with headers and at least one data row."
        ) from exc
    except pd.errors.ParserError as exc:
        raise CSVValidationError(
            "Could not parse this CSV. Check comma separators and quotation marks, "
            "then export it again with headers in the first row."
        ) from exc

    if data.empty:
        raise CSVValidationError(
            "No data rows found. Include at least one row below the headers."
        )

    return data.replace(r"^\s*$", pd.NA, regex=True)


def analyze_columns(data: pd.DataFrame, selected_columns: list[str]) -> pd.DataFrame:
    """Summarize selected columns from parse_csv(), preserving selection order.

    Count means nonblank cells, including repeated values. Numeric statistics
    require every nonblank value to be a finite number. Unavailable statistics
    are None, with a reason for the UI to display alongside N/A. Results are
    not rounded, and the original data is not modified.
    """
    result_columns = [
        "Column", "Type", "Max", "Min", "Mean", "Median", "Count", "Reason"
    ]
    results = []
    for name in selected_columns:
        if name not in data.columns:
            raise ValueError(f"Unknown column: {name}")

        values = data[name].dropna()
        result = dict.fromkeys(result_columns)
        result.update(Column=name, Count=len(values), Reason="")

        if values.empty:
            result.update(Type="Empty", Reason="No values")
        else:
            # Coercion identifies invalid values; never calculate on a subset
            # of a mixed column by silently dropping failed conversions.
            numbers = pd.to_numeric(values, errors="coerce")
            if numbers.isna().any():
                result.update(
                    Type="Text" if numbers.isna().all() else "Mixed",
                    Reason="Contains nonnumeric values",
                )
            elif not numbers.map(isfinite).all():
                result.update(
                    Type="Non-finite", Reason="Contains non-finite numbers"
                )
            else:
                result.update(
                    Type="Numeric",
                    Max=numbers.max(),
                    Min=numbers.min(),
                    Mean=numbers.mean(),
                    Median=numbers.median(),
                )
        results.append(result)

    return pd.DataFrame(results, columns=result_columns, dtype=object)
