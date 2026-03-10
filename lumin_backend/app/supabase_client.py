import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE credentials")

# Anonymous / regular backend client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Service role client (bypasses RLS)
if not SUPABASE_SERVICE_ROLE_KEY:
    raise RuntimeError("Missing SUPABASE_SERVICE_ROLE_KEY")

supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_supabase_for_jwt(jwt: str) -> Client:
    """
    Create a Supabase client authenticated with the user's JWT.
    Useful only when you WANT database RLS to enforce access.
    """
    client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(jwt)
    return client