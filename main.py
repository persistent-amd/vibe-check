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

# Health check endpoint (for uptime monitors)
from fastapi import Response

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


GROQ_API_KEY = os.getenv("GROQ_API_KEY")

class Feedback(BaseModel):
    text: str

def classify_feedback(text):
    prompt = f"""
Classify the student feedback into ONE of the following categories:

Concerns
Complaints
Negative Feedback
Appreciation
Positive Feedback
Suggestions
Questions
Neutral
Other

Feedback:
{text}

Respond with ONLY the category name.
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

    # normalize similar meanings
    normalization_map = {
        "Complaints": "Concerns",
        "Negative Feedback": "Concerns",
        "Positive Feedback": "Appreciation",
    }

    category = normalization_map.get(category, category)

    return category


@app.post("/analyze")
def analyze_feedback(feedback: Feedback):

    text = feedback.text.strip()

    if not text:
        return {"error": "Empty feedback not allowed"}

    category = classify_feedback(text)

    # 🔹 Check duplicates (case-insensitive)
    existing = (
        supabase.table("feedback")
        .select("id")
        .ilike("text", text)
        .execute()
    )

    duplicate = bool(existing.data)

    if not duplicate:
        supabase.table("feedback").insert({
            "text": text,
            "category": category
        }).execute()

    return {
        "feedback": text,
        "category": category,
        "duplicate": duplicate
    }