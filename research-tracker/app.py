"""Streamlit interface for the personal research tracker."""

import sqlite3

import streamlit as st

from db import add_item, get_items, init_db


st.set_page_config(page_title="Personal Research Tracker", page_icon="📚")
st.title("Personal Research Tracker")
st.caption("Save useful sources, keep notes, and find your research again.")

try:
    init_db()
except sqlite3.Error:
    st.error("Could not open the research database. Check that the app folder is writable.")
    st.stop()

# Reset only after a successful save; failed submissions keep the user's input.
if st.session_state.pop("item_saved", False):
    for field in ("title", "source", "notes", "tags"):
        st.session_state[field] = ""
    st.success("Research item saved. It is available in the list below when it matches your search.")

st.subheader("Add a research item")
with st.form("add_item"):
    title = st.text_input("Title (required)", key="title")
    source = st.text_input("Source", placeholder="URL, citation, or source name", key="source")
    notes = st.text_area("Notes", key="notes")
    tags = st.text_input("Tags", placeholder="e.g. climate, energy, policy", key="tags")
    st.caption("Separate tags with commas. Only the title is required.")
    submitted = st.form_submit_button("Save item")

if submitted:
    try:
        add_item(title, source, notes, tags)
    except ValueError as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error("Could not save your item. Your input is still here; please try again.")
    else:
        st.session_state.item_saved = True
        st.rerun()

st.divider()
st.subheader("Saved research")
search = st.text_input(
    "Search saved items",
    placeholder="Search titles, sources, notes, or tags",
    help="Matches partial text. Leave empty to show everything.",
)

try:
    items = get_items(search)
except sqlite3.Error:
    st.error("Could not load your saved research. Please try again.")
    st.stop()

st.caption(f"{len(items)} item(s) · Newest first")
if not items:
    if search.strip():
        st.info("No matching items. Try another search or clear the search box.")
    else:
        st.info("No research saved yet. Add your first item above.")

for item in items:
    with st.expander(item["title"], expanded=True):
        if item["source"]:
            st.text(f"Source: {item['source']}")
        if item["notes"]:
            st.text(item["notes"])
        if item["tags"]:
            st.text(f"Tags: {item['tags']}")
        st.caption(f"Saved {item['created_at']} UTC")
