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

Concern
Complaint
Negative Feedback
Appreciation
Positive Feedback
Suggestion
Question
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

    # ---- safe duplicate check ----
    try:
        resp = (
            supabase.table("feedback")
            .select("category")
            .ilike("text", text)  # keep your matching logic here (case-insensitive)
            .limit(1)
            .execute()
        )
    except Exception as e:
        # If the DB query fails, log (optional) and continue to classify normally
        # (avoids breaking user flow if Supabase temporarily errors)
        print("Supabase check error:", e)
        resp = None

    # normalize response -> ensure it's a list we can index safely
    existing_data = []
    if resp and getattr(resp, "data", None):
        # resp.data should be a list of rows; guard the type
        if isinstance(resp.data, list):
            existing_data = resp.data
        else:
            # fallback: try to coerce
            try:
                existing_data = list(resp.data)
            except Exception:
                existing_data = []

    duplicate = len(existing_data) > 0

    if duplicate:
        # safe extraction of category from the first row
        first_row = existing_data[0]
        if isinstance(first_row, dict):
            category = first_row.get("category") or "Other"
        else:
            # if the row is not a dict, coerce to string
            try:
                category = str(first_row)
            except Exception:
                category = "Other"
    else:
        # classify using LLM
        category = classify_feedback(text)
        if not category:
            category = "Other"

    # ---- Always insert the feedback (preserve frequency) ----
    try:
        supabase.table("feedback").insert({
            "text": text,
            "category": category
        }).execute()
    except Exception as e:
        # optional: fail softly and return helpful info
        print("Supabase insert error:", e)
        return {
            "feedback": text,
            "category": category,
            "duplicate": duplicate,
            "warning": "Failed to insert into DB (check server logs)"
        }

    return {
        "feedback": text,
        "category": category,
        "duplicate": duplicate
    }