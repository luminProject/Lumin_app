"""
temp_get_token.py
سكريبت مؤقت لجلب access token من Supabase
شغّليه بـ: python temp_get_token.py
"""
from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

EMAIL = "notification@gmail.com"   # ← حطي إيميلك هنا
PASSWORD = "qwerty2@"          # ← حطي كلمة المرور هنا

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

response = supabase.auth.sign_in_with_password({
    "email": EMAIL,
    "password": PASSWORD,
})

print("\n✅ Access Token:")
print(response.session.access_token)
print("\n✅ User ID:")
print(response.user.id)