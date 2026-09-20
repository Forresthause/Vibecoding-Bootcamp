import streamlit as st

st.write("Hello world")
name = st.text_input("Enter some text")
if name:
    st.write(f"Hello, {name}!")
