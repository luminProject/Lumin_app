import requests

url = "https://ldjnsziefmnckdtiqlmz.supabase.co/auth/v1/token?grant_type=password"

headers = {
    "apikey": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxkam5zemllZm1uY2tkdGlxbG16Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzEwODk3ODgsImV4cCI6MjA4NjY2NTc4OH0.9s0p2VKyS7fuhd9DrDlTj7_BQDb2wjdUR1_Ay9qLuyo",
    "Content-Type": "application/json"
}

data = {
    "email": "notification@gmail.com",
    "password": "qwerty2@"
}

response = requests.post(url, headers=headers, json=data)
print(response.json())