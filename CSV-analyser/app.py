"""Upload, preview, and analyze selected CSV columns."""

import streamlit as st

from analysis import CSVValidationError, analyze_columns, parse_csv


def reset_selection():
    """Start fresh whenever the upload changes or is removed."""
    st.session_state["selected_columns"] = []


st.set_page_config(page_title="CSV Analyser")
st.title("CSV Analyser")
st.write(
    "Upload a standard UTF-8, comma-separated CSV. "
    "The first row must contain column headers."
)

uploaded_file = st.file_uploader(
    "Upload a CSV file", type=["csv"], on_change=reset_selection
)

if uploaded_file is None:
    st.info("Choose a CSV file to preview its data.")
else:
    try:
        data = parse_csv(uploaded_file.getvalue())
    except CSVValidationError as exc:
        st.error(str(exc))
    else:
        selected_columns = st.multiselect(
            "Select columns to analyze", data.columns.tolist(), key="selected_columns"
        )

        if not selected_columns:
            st.info("Select at least one column to see its statistics.")
        else:
            results = analyze_columns(data, selected_columns)
            st.subheader("Analysis results")
            st.caption(
                "Count includes nonblank values, including duplicates. "
                "Numeric statistics ignore blanks. N/A means a statistic does not "
                "apply; see the Note column."
            )
            # Format a separate display table so numeric results stay unchanged.
            display_results = results.drop(columns=["Type"]).rename(
                columns={"Reason": "Note"}
            )
            for statistic in ("Max", "Min", "Mean", "Median"):
                display_results[statistic] = results[statistic].map(
                    lambda value: "N/A" if value is None else str(value)
                )
            st.dataframe(display_results, hide_index=True)

        st.subheader("Data preview")
        st.write(f"Rows: {len(data):,} · Columns: {len(data.columns):,}")
        st.caption(f"Showing the first {min(10, len(data))} rows. Blank cells are shown as Missing.")
        st.dataframe(data.head(10).fillna("Missing"), hide_index=True)
