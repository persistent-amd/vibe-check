from fastapi import FastAPI
from pydantic import BaseModel
import requests
import os
from dotenv import load_dotenv
from supabase import create_client
import logging
from fastapi import HTTPException

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


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def classify_feedback(text):
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY is missing")
        raise HTTPException(
            status_code=500,
            detail="AI service is not configured"
        )

    prompt = f"""
Classify the student feedback into ONE category:

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
        # "model": "llama-3.1-8b-instant",
        "model": "openai/gpt-oss-20b", # update model, old one deprecated
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        if "choices" not in result:
            logger.error(
                "Unexpected Groq response: %s",
                str(result)[:1000]
            )
            raise HTTPException(
                status_code=502,
                detail="AI provider returned an error response"
            )

        choices = result.get("choices") or []

        if not choices:
            logger.error("Groq returned an empty choices list")
            raise HTTPException(
                status_code=502,
                detail="AI provider returned no classification"
            )

        category = (
            choices[0].get("message", {}).get("content") or ""
        ).strip()

        if not category:
            logger.error("Groq returned empty classification content")
            raise HTTPException(
                status_code=502,
                detail="AI provider returned an empty classification"
            )
        normalization_map = {
            "Complaints": "Concerns",
            "Negative Feedback": "Concerns",
            "Positive Feedback": "Appreciation"
        }

        category = normalization_map.get(category, category)

        allowed_categories = {
            "Concern", "Complaint", "Negative Feedback",
            "Appreciation", "Positive Feedback",
            "Suggestion", "Question", "Neutral", "Other",
            "Concerns"
        }

        if category not in allowed_categories:
            logger.error("Unexpected category returned by Groq")
            raise HTTPException(
                status_code=502,
                detail="AI returned an unexpected category"
            )

        return category

    except requests.Timeout:
        logger.exception("Groq request timed out")
        raise HTTPException(
            status_code=504,
            detail="AI service timed out"
        )

    except requests.HTTPError as exc:
        logger.exception("Groq HTTP error")
        if exc.response is not None:
            logger.error(
                "Groq response status=%s, body=%s",
                exc.response.status_code,
                exc.response.text[:1000]
            )
        raise HTTPException(
            status_code=502,
            detail="AI service request failed"
        )
    except requests.ConnectionError:
        logger.exception("Could not connect to Groq API")
        raise HTTPException(
            status_code=502,
            detail="Could not connect to AI service"
        )

    except (requests.RequestException, ValueError, KeyError, IndexError):
        logger.exception("Groq response processing failed")
        raise HTTPException(
            status_code=502,
            detail="Could not process the AI response"
        )


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