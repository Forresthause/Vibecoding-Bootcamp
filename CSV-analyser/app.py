"""Upload, preview, and analyze selected CSV columns."""

import streamlit as st

from analysis import CSVValidationError, analyze_columns, parse_csv, prepare_plot_data


def reset_selection():
    """Start fresh whenever the upload changes or is removed."""
    st.session_state["selected_columns"] = []
    for key in ("plot_x", "plot_y", "plot_type"):
        st.session_state.pop(key, None)


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
        st.subheader("Data preview")
        st.write(f"Rows: {len(data):,} · Columns: {len(data.columns):,}")
        st.caption(f"Showing the first {min(5, len(data))} rows.")
        st.dataframe(data.head(5).fillna(""), hide_index=True)

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
                "Numeric statistics use only finite numeric cells, ignoring blanks, "
                "nonnumeric values, and infinities. N/A means no usable numbers "
                "remain; see the Note column for excluded values."
            )
            # Format a separate display table so numeric results stay unchanged.
            display_results = results.drop(columns=["Type"]).rename(
                columns={"Reason": "Note"}
            )
            for statistic in ("Max", "Min", "Mean", "Median"):
                display_results[statistic] = results[statistic].map(
                    lambda value: "N/A" if value is None else str(value)
                )
            st.table(
                display_results.style.set_properties(
                    subset=["Note"],
                    **{"white-space": "normal", "overflow-wrap": "anywhere"},
                ),
                hide_index=True,
            )

        st.subheader("Plot")
        st.caption(
            "Both axes require numeric values. Rows with a blank on either axis "
            "are omitted. Line plots connect points in ascending X order and "
            "require unique X values."
        )
        x_column = st.selectbox(
            "X column", data.columns.tolist(), index=None, key="plot_x"
        )
        y_column = st.selectbox(
            "Y column", data.columns.tolist(),
            index=None, key="plot_y"
        )
        plot_type = st.selectbox(
            "Plot type", ["Scatter", "Line"], index=None, key="plot_type"
        )
        if x_column is None or y_column is None or plot_type is None:
            st.info("Select X, Y, and a plot type to create a plot.")
        else:
            try:
                plot_data, omitted = prepare_plot_data(data, x_column, y_column, plot_type)
            except ValueError as exc:
                st.warning(str(exc))
            else:
                if omitted:
                    st.caption(f"Omitted {omitted:,} rows with a blank X or Y value.")
                chart = st.scatter_chart if plot_type == "Scatter" else st.line_chart
                chart(plot_data, x="X", y="Y", x_label=x_column, y_label=y_column)
