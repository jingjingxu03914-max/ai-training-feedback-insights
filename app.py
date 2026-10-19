from pathlib import Path
import os

import pandas as pd
import streamlit as st
from openai import OpenAI

APP_DIR = Path(__file__).parent
DATA_PATH = APP_DIR / "synthetic_training_feedback.csv"

st.set_page_config(page_title="Training Feedback Insights", page_icon="📊", layout="wide")
st.title("AI-Assisted Training Feedback Insights")
st.caption("An independent portfolio demonstration using synthetic training data only.")

@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH, parse_dates=["session_date"])
    numeric_columns = [
        "attendees", "completion_rate_pct", "confidence_before_avg",
        "confidence_after_avg", "adoption_14d_pct",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="raise")
    return df

df = load_data()

st.info(
    "Privacy by design: every row and comment in this demo is synthetic. "
    "Do not enter real patient, staff, practice or customer information."
)

regions = ["All regions"] + sorted(df["region"].unique().tolist())
selected_region = st.selectbox("Region", regions)
filtered = df if selected_region == "All regions" else df[df["region"] == selected_region]

attendees = int(filtered["attendees"].sum())
weighted_completion = (filtered["completion_rate_pct"] * filtered["attendees"]).sum() / attendees
weighted_confidence_lift = (
    (filtered["confidence_after_avg"] - filtered["confidence_before_avg"]) * filtered["attendees"]
).sum() / attendees
weighted_adoption = (filtered["adoption_14d_pct"] * filtered["attendees"]).sum() / attendees

c1, c2, c3, c4 = st.columns(4)
c1.metric("Training sessions", f"{len(filtered):,}")
c2.metric("Learners", f"{attendees:,}")
c3.metric("Avg. confidence change", f"+{weighted_confidence_lift:.1f} pts")
c4.metric("14-day adoption", f"{weighted_adoption:.0f}%")

left, right = st.columns(2)
with left:
    st.subheader("Confidence before and after training")
    confidence = filtered.set_index("session_id")[["confidence_before_avg", "confidence_after_avg"]]
    confidence.columns = ["Before", "After"]
    st.bar_chart(confidence, y_label="Average confidence (1–5)", stack=False)
with right:
    st.subheader("Adoption by training session")
    adoption = filtered.set_index("session_id")[["adoption_14d_pct"]]
    adoption.columns = ["Adoption after 14 days (%)"]
    st.bar_chart(adoption, y_label="Learners using the feature (%)")

st.subheader("Session data")
st.dataframe(
    filtered.drop(columns=["synthetic_feedback"]),
    use_container_width=True,
    hide_index=True,
)

st.subheader("AI-assisted feedback review")
st.write(
    "The model receives only aggregate metrics and the synthetic comments shown below. "
    "It is asked to identify recurring themes and suggest practical training improvements."
)
with st.expander("View the synthetic feedback used in this analysis"):
    st.dataframe(filtered[["session_id", "synthetic_feedback"]], use_container_width=True, hide_index=True)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    st.warning(
        "Live AI analysis is disabled because OPENAI_API_KEY is not set. "
        "The dashboard and metrics still work. See README.md to enable the optional AI analysis."
    )
else:
    if st.button("Generate AI insights", type="primary"):
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
        comments = "\n".join(f"- {comment}" for comment in filtered["synthetic_feedback"].tolist())
        summary = (
            f"Sessions: {len(filtered)}\nLearners: {attendees}\n"
            f"Weighted completion rate: {weighted_completion:.1f}%\n"
            f"Weighted confidence change: +{weighted_confidence_lift:.2f} points on a 1–5 scale\n"
            f"Weighted 14-day adoption: {weighted_adoption:.1f}%\n"
            f"Synthetic feedback comments:\n{comments}"
        )
        prompt = f"""You are reviewing a small, fully synthetic dataset for a digital health product training programme.

Use only the information below. Do not infer clinical outcomes or claim that these results represent a real NHS service. Return:
1. Two concise observations grounded in the metrics or comments.
2. Two practical, low-risk improvements to training or follow-up.
3. One limitation of this dataset.

Keep the response under 180 words. Clearly distinguish observed figures from suggestions.

DATA
{summary}"""
        try:
            client = OpenAI(api_key=api_key)
            response = client.responses.create(model=model, input=prompt)
            st.markdown(response.output_text)
        except Exception as exc:
            st.error(f"The AI request failed: {exc}")

st.divider()
st.caption(
    "This is a fictional portfolio prototype, not an NHS or Accurx product. "
    "Synthetic metrics must not be interpreted as evidence of real-world impact."
)
