"""CSV loading and statistics, independent of the Streamlit interface."""

from io import BytesIO
from math import isfinite

import pandas as pd


class CSVValidationError(ValueError):
    """An upload cannot be used; the message can be shown to the user."""


def prepare_plot_data(
    data: pd.DataFrame, x_column: str, y_column: str, plot_type: str
) -> tuple[pd.DataFrame, int]:
    """Return numeric X/Y pairs and a count of rows missing either value.

    Validate all nonblank values before dropping incomplete pairs. Line plots
    require unique X values among complete pairs and are sorted by X.
    Fixed output names allow the same source column on both axes.
    The input frame is never modified.
    """
    if plot_type not in ("Scatter", "Line"):
        raise ValueError("Choose Scatter or Line as the plot type.")

    converted = {}
    for axis, name in (("X", x_column), ("Y", y_column)):
        if name not in data.columns:
            raise ValueError(f"Unknown column: {name}")
        values = data[name].dropna()
        numbers = pd.to_numeric(values, errors="coerce")
        if numbers.isna().any():
            raise ValueError(
                f"{axis} column '{name}' contains nonnumeric values. "
                "Choose a numeric column."
            )
        if not numbers.map(isfinite).all():
            raise ValueError(
                f"{axis} column '{name}' contains non-finite numbers. "
                "Choose a column with finite numbers."
            )
        converted[axis] = numbers.reindex(data.index)

    pairs = pd.DataFrame(converted).dropna()
    omitted = len(data) - len(pairs)
    if pairs.empty:
        raise ValueError("No complete X/Y pairs remain. Choose columns with overlapping numeric values.")
    if plot_type == "Line":
        if pairs["X"].duplicated().any():
            raise ValueError(
                f"X column '{x_column}' has duplicate values. "
                "Use Scatter or choose an X column with unique values for Line."
            )
        pairs = pairs.sort_values("X")
    return pairs, omitted


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
    use only finite numeric cells. Excluded cells are reported in Reason.
    Unavailable statistics
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

        numbers = pd.to_numeric(values, errors="coerce")
        missing_count = len(data[name]) - len(values)
        nonnumeric_count = int(numbers.isna().sum())
        converted = numbers.dropna()
        finite = converted.map(isfinite).astype(bool)
        nonfinite_count = int((~finite).sum())
        usable = converted[finite]

        if values.empty:
            result["Type"] = "Empty"
        elif nonnumeric_count:
            result["Type"] = "Text" if numbers.isna().all() else "Mixed"
        elif nonfinite_count:
            result["Type"] = "Non-finite"
        else:
            result["Type"] = "Numeric"

        exclusions = []
        for count, label in (
            (nonnumeric_count, "nonnumeric"),
            (missing_count, "missing"),
            (nonfinite_count, "non-finite"),
        ):
            if count:
                exclusions.append(f"{count} {label} value{'s' if count != 1 else ''}")
        if exclusions:
            result["Reason"] = "Ignored " + " and ".join(exclusions) + "."

        if usable.empty:
            result["Reason"] += " No finite numeric values available."
            result["Reason"] = result["Reason"].strip()
        else:
            result.update(
                Max=usable.max(),
                Min=usable.min(),
                Mean=usable.mean(),
                Median=usable.median(),
            )
        results.append(result)

    return pd.DataFrame(results, columns=result_columns, dtype=object)
