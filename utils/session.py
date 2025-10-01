"""
Session State Management
Handles Streamlit session state initialization
"""
import streamlit as st


def init_session_state():
    """Initialize session state variables"""
    if 'manual_values' not in st.session_state:
        st.session_state.manual_values = {}

    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None