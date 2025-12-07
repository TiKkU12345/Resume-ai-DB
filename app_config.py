# """
# Configuration Helper
# Handles secrets for both Streamlit Cloud and Hugging Face Spaces
# """

# import os
# import streamlit as st


# def get_secret(key: str, default=None):
#     """Get secret from environment or Streamlit secrets"""
#     # Try environment variable first
#     value = os.getenv(key)
#     if value:
#         return value
    
#     # Fall back to Streamlit secrets
#     try:
#         return st.secrets[key]
#     except (KeyError, FileNotFoundError):
#         return default
