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
    page_title="Campus Feedback Vibe Check Dashboard",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
<style>

/* Gradient Title */
.gradient-text {
    font-size: 42px;
    font-weight: 800;
    background: linear-gradient(90deg,#6EE7B7,#3B82F6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 15px;
    border-radius: 12px;
}

/* Section spacing */
.block-container {
    padding-top: 2rem;
}

/* Divider styling */
hr {
    border: none;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin-top: 20px;
    margin-bottom: 20px;
}

</style>
""", unsafe_allow_html=True)


import requests
# ---------- HEADER ----------
col1, col2 = st.columns([4,1])

with col1:
    st.markdown('<div class="gradient-text">Feedback Vibe Check Dashboard</div>', unsafe_allow_html=True)
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


# # ---------- previous MODERN HEADER ----------
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
result_container = st.empty()
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

with result_container:
    if "last_result" in st.session_state:
        if st.session_state.last_result["duplicate"]:
            st.info(
                f"🔁 Similar feedback detected\n\nCategory: **{st.session_state.last_result['category']}**\n\nStored for trend analysis."
            )
        else:
            st.success(
                f"✅ Category: **{st.session_state.last_result['category']}**"
            )

        del st.session_state.last_result

# ---------- CSV UPLOAD ----------
st.subheader("📂 Batch Feedback Upload CSV")

uploaded_file = st.file_uploader(
    "Upload CSV with a column named 'text'",
    type=["csv"]
)

if uploaded_file:

    bulk_df = pd.read_csv(uploaded_file)

    if "text" not in bulk_df.columns:
        st.error("CSV must contain a column named 'text'")
    else:

        st.info(f"{len(bulk_df)} feedback entries detected")

        st.write("Preview:")
        st.dataframe(bulk_df.head())

        if st.button("Analyze CSV Feedback", use_container_width=True):

            new_count = 0
            reused_count = 0

            progress = st.progress(0)

            for i, text in enumerate(bulk_df["text"]):

                try:
                    response = requests.post(API_URL, json={"text": text})

                    if response.status_code == 200:
                        result = response.json()

                        if result.get("duplicate"):
                            reused_count += 1
                        else:
                            new_count += 1

                except:
                    pass

                progress.progress((i + 1) / len(bulk_df))

            st.success(
                f"""
CSV processed successfully!

New classifications: {new_count}
Reused classifications: {reused_count}
Total processed: {len(bulk_df)}
"""
            )

            st.rerun()

st.divider()
# ---------- DISPLAY DATA ----------
if data:

    df = pd.DataFrame(data)

    # ----- CATEGORY NORMALIZATION FOR ANALYTICS -----
    category_map = {
        "Concern": "Concern",
        "Complaint": "Concern",
        "Negative Feedback": "Concern",

        "Appreciation": "Appreciation",
        "Positive Feedback": "Appreciation",

        "Suggestion": "Suggestion",

        "Question": "Question",

        "Neutral": "Other",
        "Other": "Other"
    }

    df["main_category"] = df["category"].map(category_map).fillna("Other")

    # Sort newest first
    if "created_at" in df.columns:
        df = df.sort_values(by="created_at", ascending=False)

    # ---------- METRICS ----------
    st.subheader("📊 Overview")

    counts = df["main_category"].value_counts()

    metrics = {
        "Total Feedback": len(df),
        "Concerns": counts.get("Concern", 0),
        "Appreciation": counts.get("Appreciation", 0),
        "Suggestions": counts.get("Suggestion", 0),
        "Questions": counts.get("Question", 0)
    }

    cols = st.columns(len(metrics))

    for col, (label, value) in zip(cols, metrics.items()):
        col.metric(label, value)

    # ---------- CHARTS ----------
    st.subheader("📈 Sentiment Analytics")

    colA, colB = st.columns(2)

    category_counts = df["main_category"].value_counts()

    # Bar chart
    colA.bar_chart(category_counts)

    # Pie chart
    pie = px.pie(
        values=category_counts.values,
        names=category_counts.index,
        title="Category Distribution",
        hole=0.45
    )

    colB.plotly_chart(pie, use_container_width=True)

    st.divider()

    # ---------- TREND GRAPH ----------
    st.subheader("📉 Sentiment Trend Over Time")

    if "created_at" in df.columns:

        df["created_at"] = pd.to_datetime(df["created_at"])
        df["date"] = df["created_at"].dt.date

        trend = df.groupby(["date", "main_category"]).size().reset_index(name="count")

        trend_chart = px.line(
            trend,
            x="date",
            y="count",
            color="main_category",
            markers=True
        )

        st.plotly_chart(trend_chart, use_container_width=True)

    else:
        st.info("Trend data will appear as more feedback is collected.")

    # ---------- ALERT SYSTEM ----------
    st.subheader("🚨 Alerts")

    alerts = []

    if "created_at" in df.columns:

        df["created_at"] = pd.to_datetime(df["created_at"])

        now = pd.Timestamp.now()
        last_24h = df[df["created_at"] > now - pd.Timedelta(hours=24)]
        prev_24h = df[(df["created_at"] <= now - pd.Timedelta(hours=24)) &
                    (df["created_at"] > now - pd.Timedelta(hours=48))]

        # 1️⃣ Concern spike detection
        concern_last = (last_24h["main_category"] == "Concern").sum()
        concern_prev = (prev_24h["main_category"] == "Concern").sum()

        if concern_prev > 0:
            change = ((concern_last - concern_prev) / concern_prev) * 100

            if change > 50:
                alerts.append(f"🚨 Concern spike detected (+{int(change)}% in last 24h)")

        # 2️⃣ Keyword issue detection
        issue_keywords = {
            "wifi": "📶 WiFi complaints rising",
            "hostel": "🏠 Hostel related complaints increasing",
            "food": "🍽 Cafeteria complaints detected",
            "library": "📚 Library related feedback rising",
            "internet": "🌐 Internet connectivity issues reported"
        }

        text_lower = df["text"].str.lower()

        for keyword, message in issue_keywords.items():
            count = text_lower.str.contains(keyword).sum()

            if count >= 3:
                alerts.append(f"{message} ({count} mentions)")

        # 3️⃣ Unanswered questions
        question_count = (df["main_category"] == "Question").sum()

        if question_count >= 3:
            alerts.append(f"❓ {question_count} student questions need attention")

        # 4️⃣ Negative sentiment trend
        negative_ratio = (df["main_category"] == "Concern").sum() / len(df)

        if negative_ratio > 0.4:
            alerts.append("📉 Negative sentiment is unusually high")

    # ---------- DISPLAY ALERTS ----------

    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("✅ No critical issues detected")

    # ---------- ISSUE CLUSTERING ----------
    st.subheader("🔥 Top Campus Issues")

    issue_keywords = {
        "wifi": "WiFi Connectivity",
        "internet": "Internet Issues",
        "hostel": "Hostel Facilities",
        "food": "Cafeteria / Food",
        "canteen": "Cafeteria / Food",
        "library": "Library Facilities",
        "charging": "Charging Ports",
        "network": "Network Problems",
        "cleanliness": "Campus Cleanliness"
    }

    issue_counts = {}

    for keyword, issue_name in issue_keywords.items():
        count = df["text"].str.lower().str.contains(keyword).sum()

        if count > 0:
            issue_counts[issue_name] = issue_counts.get(issue_name, 0) + count

    if issue_counts:

        issue_df = pd.DataFrame(
            issue_counts.items(),
            columns=["Issue", "Mentions"]
        ).sort_values("Mentions", ascending=False)

        # show top 5
        top_issues = issue_df.head(5)

        st.table(top_issues)

        # visual chart
        issue_chart = px.bar(
            top_issues,
            x="Mentions",
            y="Issue",
            orientation="h",
            title="Most Reported Campus Issues"
        )

        st.plotly_chart(issue_chart, use_container_width=True)

    else:
        st.info("No issue patterns detected yet.")

    # ---------- TABLE ----------
    st.subheader("🗂 Feedback Log")

    display_df = df.copy()

    # ensure datetime format
    if "created_at" in display_df.columns:
        display_df["created_at"] = pd.to_datetime(display_df["created_at"])

        # sort newest first
        display_df = display_df.sort_values(by="created_at", ascending=False)

        # format AFTER sorting
        display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M")

    # add category indicators
    category_badges = {
        "Concern": "🔴 Concern",
        "Complaint": "🔴 Complaint",
        "Negative Feedback": "🔴 Negative Feedback",

        "Appreciation": "🟢 Appreciation",
        "Positive Feedback": "🟢 Positive Feedback",

        "Suggestion": "🟡 Suggestion",
        "Question": "❓ Question",

        "Neutral": "⚪ Neutral",
        "Other": "⚪ Other"
    }

    display_df["category"] = display_df["category"].map(category_badges).fillna(display_df["category"])

    # keep required columns
    display_df = display_df[["text", "category", "created_at"]]

    # rename for UI
    display_df.columns = ["Feedback", "Category", "Time"]

    # add row numbering
    display_df.index = pd.Index(range(1, len(display_df)+1))

    st.dataframe(display_df, use_container_width=True)