"""
Database module for Supabase connection.
Provides a cached Supabase client to avoid re-initialization on page reloads.
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def init_connection() -> Client:
    """
    Initialize a cached Supabase client using secrets.
    
    Returns:
        Client: Authenticated Supabase client instance.
    """
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# Export the cached supabase client
supabase = init_connection()
