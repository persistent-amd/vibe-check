import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL") or st.secrets.get("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Supabase credentials missing")
    st.stop()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials not found in .env file")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# API_URL = "http://127.0.0.1:8000/analyze"

API_URL = "https://vibe-check-g1at.onrender.com/analyze"

st.set_page_config(
    page_title="Vibe Check Dashboard",
    page_icon="🎓",
    layout="wide"
)

# ---------- MODERN HEADER ----------
st.markdown("""
    <h1 style='text-align: center;'>🎓 Vibe Check Dashboard</h1>
    <p style='text-align: center; font-size:18px; color:gray;'>
    Real-time student sentiment intelligence
    </p>
""", unsafe_allow_html=True)

st.divider()

# ---------- SESSION STORAGE ----------
if "data" not in st.session_state:
    try:
        response = supabase.table("feedback").select("*").order("created_at").execute()
        st.session_state.data = response.data if response.data else []
    except:
        st.session_state.data = []

# ---------- INPUT CARD ----------
st.subheader("📝 Submit Feedback")

feedback_text = st.text_area(
    "Enter student feedback:",
    placeholder="Example: Hostel WiFi is unusable at night..."
)

if st.button("Analyze Feedback", use_container_width=True):
    if feedback_text.strip() != "":
        try:
            response = requests.post(API_URL, json={"text": feedback_text})
            result = response.json()

            category = result["category"]

            st.success(f"✅ Category: {category}")

            st.session_state.data.append({
                "feedback": feedback_text,
                "category": category,
                "time": datetime.now().strftime("%H:%M:%S")
            })

        except:
            st.error("⚠️ Cannot connect to AI server. Make sure FastAPI is running.")
    else:
        st.warning("Please enter feedback")

st.divider()

# ---------- DISPLAY DATA ----------
if st.session_state.data:

    df = pd.DataFrame(st.session_state.data)

    # ---------- METRICS ----------
    st.subheader("📊 Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Concerns", (df["category"] == "Concern").sum())
    col2.metric("Appreciation", (df["category"] == "Appreciation").sum())
    col3.metric("Suggestions", (df["category"] == "Suggestion").sum())

    st.divider()

    # ---------- CHARTS ----------
    st.subheader("📈 Sentiment Analytics")

    colA, colB = st.columns(2)

    category_counts = df["category"].value_counts()

    # Bar chart
    colA.bar_chart(category_counts)

    # Pie chart (modern)
    pie = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title="Category Distribution",
        hole=0.45   # donut style (modern look)
    )
    colB.plotly_chart(pie, use_container_width=True)

    st.divider()

    # ---------- TABLE ----------
    st.subheader("🗂 Feedback Log")
    st.dataframe(df, use_container_width=True)