from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


SUPABASE_URL = os.getenv("SUPABASE_URL") or ""
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or ""

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class Feedback(BaseModel):
    text: str

def classify_feedback(text):
    prompt = f"""
Classify the student feedback into one category:

Categories:
1. Concern
2. Appreciation
3. Suggestion

Feedback:
{text}

Respond with only the category name.
"""

    url = "https://api.groq.com/openai/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    response = requests.post(url, headers=headers, json=data)
    result = response.json()

    category = result["choices"][0]["message"]["content"].strip()

    return category


@app.post("/analyze")
def analyze_feedback(feedback: Feedback):
    category = classify_feedback(feedback.text)

    # 🔹 INSERT INTO SUPABASE
    response = supabase.table("feedback").insert({
        "text": feedback.text,
        "category": category
    }).execute()

    #print("SUPABASE RESPONSE:", response)   # ADD THIS LINE for debug table insertions

    return {
        "feedback": feedback.text,
        "category": category
    }