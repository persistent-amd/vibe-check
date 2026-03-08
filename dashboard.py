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

import requests
import streamlit as st

# Wake backend on first dashboard load
if "backend_warmed" not in st.session_state:
    try:
        requests.get(API_URL.replace("/analyze", "/docs"), timeout=5)
        st.session_state.backend_warmed = True
    except:
        pass

st.set_page_config(
    page_title="Feedback Vibe Check Dashboard",
    page_icon="🎓",
    layout="wide"
)


import requests
# ---------- HEADER ----------
col1, col2 = st.columns([4,1])

with col1:
    st.title("Feedback Vibe Check Dashboard")
    st.caption("AI-powered campus feedback intelligence • FastAPI + LLM + Supabase + Streamlit")

with col2:
    try:
        r = requests.get(API_URL.replace("/analyze", "/health"), timeout=3)

        if r.status_code == 200:
            st.success("🟢 System Online")

        else:
            st.warning("🟡 Waking up")

    except:
        st.error("🔴 Offline")

st.info(
    "⏳ If inactive, the backend may take **up to 60 seconds** to wake up "
    "(free cloud hosting). After waking, responses take ~2 seconds."
)


# # ---------- MODERN HEADER ----------
# st.markdown("""
#     <h1 style='text-align: center;'>Feedback Vibe Check Dashboard</h1>
#     <p style='text-align: center; font-size:18px; color:gray;'>
#     Real-time student sentiment intelligence
#     </p>
# """, unsafe_allow_html=True)

# st.caption("⚡ AI feedback analysis powered by FastAPI, LLM inference, Supabase, and Streamlit.")

# st.info(
#     "⏳ If the system has been inactive, the backend may take up to **60 seconds** "
#     "to wake up on the first request (free cloud hosting). "
#     "Subsequent requests respond in ~2 seconds."
# )

# # backend status indicator
# try:
#     r = requests.get(API_URL.replace("/analyze", "/health"), timeout=3)
#     if r.status_code == 200:
#         st.success("🟢 AI Backend Online")
#     else:
#         st.warning("🟡 Backend waking up... may take up to 60 seconds")
# except:
#     st.error("🔴 Backend offline, submit feedback to wake it up")

# st.divider()

# ---------- FETCH LATEST DATA ----------
try:
    response = supabase.table("feedback") \
        .select("*") \
        .order("created_at", desc=True) \
        .execute()

    data = response.data if response.data else []

except Exception as e:
    data = []

# ---------- INPUT CARD ----------
st.subheader("📝 Submit Feedback (Single)")

feedback_text = st.text_area(
    "Enter student feedback:",
    placeholder="Example: Hostel WiFi is unusable at night..."
)

if st.button("Analyze Feedback", use_container_width=True):

    if feedback_text.strip() != "":
        try:
            with st.spinner("Analyzing feedback..."):
                response = requests.post(API_URL, json={"text": feedback_text})

            if response.status_code == 200:
                result = response.json()
                category = result["category"]

                st.session_state.last_result = {
                    "duplicate": result.get("duplicate"),
                    "category": category
                }

                st.rerun()

            else:
                st.error("⚠️ Server error. Please try again.")

        except requests.exceptions.RequestException:
            st.error("⚠️ Cannot reach AI server. It may be waking up.")

    else:
        st.warning("Please enter feedback")

st.divider()

# ---------- CSV UPLOAD ----------
st.subheader("📂 Batch Feedback Upload CSV")

uploaded_file = st.file_uploader(
    "Upload CSV with a column named 'text'",
    type=["csv"]
)

if uploaded_file:
    bulk_df = pd.read_csv(uploaded_file)

    if "text" in bulk_df.columns:
        for text in bulk_df["text"]:
            try:
                requests.post(API_URL, json={"text": text})
            except:
                st.error("Error uploading some entries")

        st.success("Bulk feedback processed successfully!")
        st.rerun()   # reload dashboard with fresh DB data
    else:
        st.error("CSV must contain a column named 'text'")


# Show last result message after rerun
if "last_result" in st.session_state:
    if st.session_state.last_result["duplicate"]:
        st.warning(
            f"⚠️ Already exists → Category: {st.session_state.last_result['category']}"
        )
    else:
        st.success(
            f"✅ Category: {st.session_state.last_result['category']}"
        )

    del st.session_state.last_result


# ---------- DISPLAY DATA ----------
if data:

    df = pd.DataFrame(data)

# Sort newest first
if "created_at" in df.columns:
    df = df.sort_values(by="created_at", ascending=False)

    # ---------- METRICS ----------
    st.subheader("📊 Overview")

    col1, col2, col3, col4 = st.columns(4, gap="large")

    st.metric("Total Feedback", len(df))
    col1.metric("Concerns", (df["category"] == "Concerns").sum())
    col2.metric("Appreciation", (df["category"] == "Appreciation").sum())
    col3.metric("Suggestions", (df["category"] == "Suggestions").sum())
    col4.metric("Questions", (df["category"] == "Questions").sum())

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

    # ---------- TREND GRAPH ----------
    st.subheader("📉 Sentiment Trend Over Time")

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])
        df["date"] = df["created_at"].dt.date

        trend = df.groupby(["date", "category"]).size().reset_index(name="count")

        trend_chart = px.line(
            trend,
            x="date",
            y="count",
            color="category",
            markers=True
        )

        st.plotly_chart(trend_chart, use_container_width=True)
    else:
        st.info("Trend data will appear as more feedback is collected.")

    # ---------- CONCERN ALERT ----------
    st.subheader("🚨 Alerts")

    concern_count = (df["category"] == "Concern").sum()
    total = len(df)

    if total > 0:
        concern_ratio = concern_count / total

        if concern_ratio > 0.5:
            st.error("⚠️ High number of concerns detected!")
        elif concern_ratio > 0.3:
            st.warning("⚠️ Concerns are rising.")
        else:
            st.success("✅ Student sentiment stable.")

    # ---------- TABLE ----------
    st.subheader("🗂 Feedback Log")
    # Clean & format table
    display_df = df.copy()

    if "created_at" in display_df.columns:
        display_df["created_at"] = pd.to_datetime(display_df["created_at"]).dt.strftime("%Y-%m-%d %H:%M")

    display_df = display_df[["text", "category", "created_at"]]

    display_df.columns = ["Feedback", "Category", "Time"]

    st.dataframe(display_df, use_container_width=True)