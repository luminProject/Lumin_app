"""
Supabase Client Configuration

This module initializes the connection with Supabase
and provides helper functions for authenticated requests.
"""

import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE credentials")


# Base client (anonymous access)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_supabase_for_jwt(jwt: str) -> Client:
    """
    Create a Supabase client authenticated with the user's JWT.

    This is required for Row Level Security (RLS) policies
    that depend on auth.uid().
    """

    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Attach JWT token to PostgREST requests
    client.postgrest.auth(jwt)

    return client