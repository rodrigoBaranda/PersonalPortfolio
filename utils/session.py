"""
Session State Management
Handles Streamlit session state initialization
"""
import streamlit as st
from utils import get_logger


logger = get_logger(__name__)


def init_session_state():
    """Initialize session state variables"""
    if 'manual_values' not in st.session_state:
        st.session_state.manual_values = {}
        logger.debug("Initialized manual_values in session state")

    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = None
        logger.debug("Initialized last_refresh in session state")
