"""Run with: python3 -m unittest discover -s CSV-analyser -v"""

import unittest

import pandas as pd

from analysis import CSVValidationError, analyze_columns, parse_csv, prepare_plot_data


class ParseCSVTests(unittest.TestCase):
    def test_reads_headers_and_preserves_cell_text(self):
        data = parse_csv(b"Client,Revenue,Code\nAcme,100,001\nBeta,300,002\n")
        self.assertEqual(list(data.columns), ["Client", "Revenue", "Code"])
        self.assertEqual(data.shape, (2, 3))
        self.assertEqual(data.iloc[0].tolist(), ["Acme", "100", "001"])

    def test_handles_quoted_commas_newlines_and_escaped_quotes(self):
        data = parse_csv(
            b'Client,Note\n"North, Inc.","First line\nSecond ""quoted"" line"\n'
        )
        self.assertEqual(data.iloc[0, 0], "North, Inc.")
        self.assertEqual(data.iloc[0, 1], 'First line\nSecond "quoted" line')

    def test_accepts_utf8_with_or_without_bom(self):
        for encoding in ("utf-8", "utf-8-sig"):
            with self.subTest(encoding=encoding):
                data = parse_csv("Client,Revenue\n上海,100\n".encode(encoding))
                self.assertEqual(list(data.columns), ["Client", "Revenue"])
                self.assertEqual(data.iloc[0, 0], "上海")

    def test_normalizes_only_blank_cells_to_missing(self):
        data = parse_csv(b"Client,Revenue,Note\nAcme,,NA\nBeta,   ,null\n")
        self.assertTrue(data["Revenue"].isna().all())
        self.assertEqual(data["Note"].tolist(), ["NA", "null"])

    def test_skips_blank_lines(self):
        data = parse_csv(b"Client,Revenue\n\nAcme,100\n\nBeta,200\n")
        self.assertEqual(len(data), 2)

    def test_accepts_single_column(self):
        data = parse_csv(b"Client\nAcme\nBeta\n")
        self.assertEqual(data["Client"].tolist(), ["Acme", "Beta"])

    def test_rejects_empty_or_blank_file(self):
        for content in (b"", b"\n   \n"):
            with self.subTest(content=content):
                with self.assertRaisesRegex(CSVValidationError, "No data"):
                    parse_csv(content)

    def test_rejects_headers_without_rows(self):
        with self.assertRaisesRegex(CSVValidationError, "No data rows"):
            parse_csv(b"Client,Revenue\n")

    def test_rejects_invalid_utf8(self):
        with self.assertRaisesRegex(CSVValidationError, "UTF-8"):
            parse_csv(b"Client\n\xff\n")

    def test_reports_parser_errors(self):
        for content in (
            b'Client,Revenue\n"Acme,100\n',
            b"Client,Revenue\nAcme,100\nBeta,200,extra\n",
        ):
            with self.subTest(content=content):
                with self.assertRaisesRegex(CSVValidationError, "Could not parse"):
                    parse_csv(content)


class AnalyzeColumnsTests(unittest.TestCase):
    def analyze_values(self, values):
        data = parse_csv(("Value,Other\n" + "\n".join(
            f"{value},x" for value in values
        )).encode("utf-8"))
        return analyze_columns(data, ["Value"]).iloc[0]

    def assert_unavailable(self, result, expected_type, count):
        self.assertEqual(result["Type"], expected_type)
        self.assertEqual(result["Count"], count)
        self.assertTrue(result["Reason"])
        for statistic in ("Max", "Min", "Mean", "Median"):
            self.assertIsNone(result[statistic])

    def test_numeric_statistics_with_odd_median(self):
        result = self.analyze_values(["9", "1", "2"])
        self.assertEqual(result["Type"], "Numeric")
        self.assertEqual(result["Max"], 9)
        self.assertEqual(result["Min"], 1)
        self.assertEqual(result["Mean"], 4)
        self.assertEqual(result["Median"], 2)
        self.assertEqual(result["Count"], 3)
        self.assertEqual(result["Reason"], "")

    def test_decimals_negatives_scientific_notation_and_even_median(self):
        result = self.analyze_values(["-2.5", "0", "1.5", "1e1"])
        self.assertEqual(result["Max"], 10)
        self.assertEqual(result["Min"], -2.5)
        self.assertEqual(result["Mean"], 2.25)
        self.assertEqual(result["Median"], 0.75)

    def test_blanks_are_excluded_but_duplicates_count(self):
        result = self.analyze_values(["2", "", "   ", "2", "8"])
        self.assertEqual(result["Count"], 3)
        self.assertEqual(result["Mean"], 4)
        self.assertEqual(result["Median"], 2)

    def test_single_numeric_value(self):
        result = self.analyze_values(["7"])
        for statistic in ("Max", "Min", "Mean", "Median"):
            self.assertEqual(result[statistic], 7)
        self.assertEqual(result["Count"], 1)

    def test_text_column(self):
        self.assert_unavailable(
            self.analyze_values(["Alice", "Bob", "Alice", ""]), "Text", 3
        )

    def test_mixed_column_does_not_average_numeric_subset(self):
        self.assert_unavailable(
            self.analyze_values(["100", "300", "pending"]), "Mixed", 3
        )

    def test_empty_column(self):
        self.assert_unavailable(self.analyze_values(["", "   "]), "Empty", 0)

    def test_nonfinite_values_do_not_produce_numeric_statistics(self):
        for value in ("inf", "-inf", "NaN", "NA"):
            with self.subTest(value=value):
                result = self.analyze_values(["1", value])
                self.assert_unavailable(
                    result, "Non-finite" if "inf" in value else "Mixed", 2
                )

    def test_formatted_values_are_not_automatically_converted(self):
        for value in ('"1,000"', "$20", "10%", "2026-09-24"):
            with self.subTest(value=value):
                self.assert_unavailable(self.analyze_values([value]), "Text", 1)

    def test_selection_order_and_original_data_preserved(self):
        data = parse_csv(b"Name,Revenue,Cost\nAcme,100,20\nBeta,300,40\n")
        original = data.copy(deep=True)
        results = analyze_columns(data, ["Cost", "Name"])
        self.assertEqual(results["Column"].tolist(), ["Cost", "Name"])
        self.assertEqual(results["Type"].tolist(), ["Numeric", "Text"])
        self.assertEqual(results.iloc[0]["Mean"], 30)
        pd.testing.assert_frame_equal(data, original)

    def test_empty_selection_returns_empty_results_with_headers(self):
        results = analyze_columns(parse_csv(b"Value\n1\n"), [])
        self.assertTrue(results.empty)
        self.assertIn("Count", results.columns)

    def test_unknown_column_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unknown column: Missing"):
            analyze_columns(parse_csv(b"Value\n1\n"), ["Missing"])


class PreparePlotDataTests(unittest.TestCase):
    def test_converts_pairs_omits_blanks_and_preserves_original(self):
        data = parse_csv(b"a,b\n3,1e1\n1,-2.5\n,8\n4,\n")
        original = data.copy(deep=True)
        pairs, omitted = prepare_plot_data(data, "a", "b", "Scatter")
        self.assertEqual(pairs["X"].tolist(), [3, 1])
        self.assertEqual(pairs["Y"].tolist(), [10, -2.5])
        self.assertEqual(omitted, 2)
        pd.testing.assert_frame_equal(data, original)

    def test_rejects_invalid_values_on_either_axis_even_in_incomplete_rows(self):
        for value in ("text", "NaN", "NA", "$20", "inf", "-inf"):
            for axis in ("X", "Y"):
                with self.subTest(value=value, axis=axis):
                    row = f"{value}," if axis == "X" else f",{value}"
                    data = parse_csv(f"a,b\n1,2\n{row}\n".encode())
                    with self.assertRaisesRegex(ValueError, f"{axis} column"):
                        prepare_plot_data(data, "a", "b", "Scatter")

    def test_rejects_text_only_column(self):
        data = parse_csv(b"a,b\nAlice,2\nBob,3\n")
        with self.assertRaisesRegex(ValueError, "nonnumeric"):
            prepare_plot_data(data, "a", "b", "Scatter")

    def test_rejects_empty_or_nonoverlapping_pairs(self):
        for content in (b"a,b\n,1\n,2\n", b"a,b\n1,\n,2\n"):
            with self.subTest(content=content):
                with self.assertRaisesRegex(ValueError, "No complete X/Y pairs"):
                    prepare_plot_data(parse_csv(content), "a", "b", "Scatter")

    def test_line_sorts_numerically_and_ignores_incomplete_duplicates(self):
        data = parse_csv(b"a,b\n10,100\n2,20\n2,\n")
        pairs, omitted = prepare_plot_data(data, "a", "b", "Line")
        self.assertEqual(pairs.values.tolist(), [[2, 20], [10, 100]])
        self.assertEqual(omitted, 1)

    def test_duplicate_x_is_allowed_only_for_scatter(self):
        data = parse_csv(b"a,b\n1,2\n1.0,3\n")
        pairs, _ = prepare_plot_data(data, "a", "b", "Scatter")
        self.assertEqual(len(pairs), 2)
        with self.assertRaisesRegex(ValueError, "Use Scatter"):
            prepare_plot_data(data, "a", "b", "Line")

    def test_same_column_on_both_axes_and_single_point(self):
        data = parse_csv(b"a\n7\n")
        for plot_type in ("Scatter", "Line"):
            with self.subTest(plot_type=plot_type):
                pairs, omitted = prepare_plot_data(data, "a", "a", plot_type)
                self.assertEqual(pairs.values.tolist(), [[7, 7]])
                self.assertEqual(omitted, 0)

    def test_rejects_unknown_columns_and_plot_types(self):
        data = parse_csv(b"a,b\n1,2\n")
        for x, y in (("missing", "b"), ("a", "missing")):
            with self.assertRaisesRegex(ValueError, "Unknown column"):
                prepare_plot_data(data, x, y, "Scatter")
        with self.assertRaisesRegex(ValueError, "Choose Scatter or Line"):
            prepare_plot_data(data, "a", "b", "Bar")


if __name__ == "__main__":
    unittest.main()
