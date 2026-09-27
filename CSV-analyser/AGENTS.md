# CSV Analyser

## Project context
- A Python app for uploading, previewing, and analyzing CSV data.
- Uses Streamlit for the UI and pandas for data handling.
- Dependencies are declared in requirements.txt.

## Development principles
- Keep parsing and analysis in analysis.py, independent of Streamlit.
- Keep UI flow, session state, and display formatting in app.py.
- Preserve existing behavior unless the task calls for changing it.
- Do not introduce new CSV interpretation or statistical behavior implicitly.
- Explicitly requested behavior changes are welcome; update relevant tests.
- Keep validation errors understandable to users.
- Prefer the simplest architecture that satisfies the requested behavior; avoid unnecessary files, abstractions, and dependencies.
- After making changes, briefly explain what changed and why.

## Testing
- Tests use unittest and live in test_analysis.py.
- From the repository root: `python3 -m unittest discover -s CSV-analyser -v`.
- Add regression coverage for changed parsing and analysis behavior.
- For UI changes, run `streamlit run CSV-analyser/app.py` and check affected flows manually.
