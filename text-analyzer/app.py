import re
from collections import Counter

import streamlit as st


def clear_text():
    st.session_state["text_input"] = ""


# Page and input form
st.set_page_config(page_title="Text Analyzer")
st.title("Text Analyzer")
st.write("Enter some text to see its basic stats.")

with st.form("text_form"):
    text = st.text_area("Your text", height=200, key="text_input")
    submitted = st.form_submit_button("Analyze")
    st.form_submit_button("Clear", on_click=clear_text)


# Analyze only after the form is submitted.
if submitted:
    if not text.strip():
        st.info("Please enter some text to analyze.")
    else:
        # Keep contractions together and normalize case and curly apostrophes.
        words = re.findall(r"[^\W_]+(?:'[^\W_]+)*", text.lower().replace("’", "'"))
        sentences = [part for part in re.split(r"[.!?]+", text) if re.search(r"\w", part)]
        common_words = Counter(words).most_common(5)

        # Display the counts and word-frequency table.
        word_column, character_column, sentence_column = st.columns(3)
        word_column.metric("Words", len(words))
        character_column.metric("Characters", len(text))
        sentence_column.metric("Sentences (estimated)", len(sentences))
        st.caption("Characters include spaces and line breaks. Sentences are estimated using . ! ?")

        st.subheader("Five most common words")
        if common_words:
            rows = []
            previous_count = None
            rank = 0
            for position, (word, count) in enumerate(common_words, start=1):
                # Ties share a rank; the next rank skips the tied positions.
                if count != previous_count:
                    rank = position
                rows.append({"Rank": rank, "Word": word, "Count": count})
                previous_count = count
            st.table(rows, hide_index=True)
        else:
            st.info("No words found.")
