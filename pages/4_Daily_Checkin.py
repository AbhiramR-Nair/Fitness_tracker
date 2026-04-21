"""
Pages: Daily Check-In - Anthropometric & Recovery Logging (Session-Based UPSERT)
Combined body metrics and recovery tracking with historical trends and state management.
Schema: daily_telemetry (log_id UUID, date UNIQUE, weight, sleep, rhr, pain metrics)
        tape_measurements (log_id UUID, date UNIQUE, waist, shoulders, chest, arms, legs)
Features:
  - Session-based pending_checkin staging workflow
  - Independent UPSERT logic for daily_telemetry and tape_measurements
  - Multi-axis Plotly trend graph (last 30 days)
  - Completed today sidebar with visual indicators
  - Stage buttons for each data section
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from database import supabase

# ============================================================================
# PAGE CONFIG & STATE INITIALIZATION
# ============================================================================

st.set_page_config(page_title="Daily Check-In - Protocol Telemetry", layout="wide")
st.header("Daily Check-In")

# Initialize session state for pending check-in data
if "pending_checkin" not in st.session_state:
    st.session_state.pending_checkin = {}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_todays_telemetry() -> dict:
    """Query daily_telemetry for today's entry (if exists)."""
    try:
        today = str(datetime.now().date())
        resp = (
            supabase.table("daily_telemetry")
            .select("*")
            .eq("date", today)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        st.warning(f"Error fetching today's telemetry: {e}")
        return None


def get_todays_tape_measurements() -> dict:
    """Query tape_measurements for today's entry (if exists)."""
    try:
        today = str(datetime.now().date())
        resp = (
            supabase.table("tape_measurements")
            .select("*")
            .eq("date", today)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        st.warning(f"Error fetching today's tape measurements: {e}")
        return None


def get_last_30_days() -> pd.DataFrame:
    """Query last 30 days of daily_telemetry data."""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)

        resp = (
            supabase.table("daily_telemetry")
            .select("date, daily_weight, sleep_hrs, rhr")
            .gte("date", str(start_date))
            .lte("date", str(end_date))
            .order("date", desc=False)
            .execute()
        )

        if resp.data:
            df = pd.DataFrame(resp.data)
            df["date"] = pd.to_datetime(df["date"])
            df["daily_weight"] = pd.to_numeric(df["daily_weight"], errors="coerce")
            df["sleep_hrs"] = pd.to_numeric(df["sleep_hrs"], errors="coerce")
            df["rhr"] = pd.to_numeric(df["rhr"], errors="coerce")
            return df
        return pd.DataFrame()
    except Exception as e:
        st.warning(f"Error fetching 30-day history: {e}")
        return pd.DataFrame()


def create_trend_graph(df: pd.DataFrame) -> go.Figure:
    """Create multi-axis Plotly line graph for weight, sleep, RHR."""
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for trend graph.")
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Weight (left y-axis)
    if "daily_weight" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["daily_weight"],
                mode="lines+markers",
                name="Weight (kg)",
                line=dict(color="#FF6B6B", width=2),
                yaxis="y1",
            ),
            secondary_y=False
        )

    # RHR (right y-axis 2)
    if "rhr" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["rhr"],
                mode="lines+markers",
                name="RHR (bpm)",
                line=dict(color="#FFE66D", width=2),
                yaxis="y3",
            ),
            secondary_y=False
        )

    # Sleep (right y-axis 1)
    if "sleep_hrs" in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["sleep_hrs"],
                mode="lines+markers",
                name="Sleep (hrs)",
                line=dict(color="#4ECDC4", width=2),
                yaxis="y2",
            ),
            secondary_y=True
        )


    # Configure axes
    fig.update_layout(
        title="📊 Last 30 Days: Weight, Sleep & RHR Trends",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    fig.update_yaxes(title_text="Weight (kg)/RHR (bpm)", secondary_y=False, showgrid=False)
    fig.update_yaxes(title_text="Sleep (hrs)", secondary_y=True, showgrid=False)

    return fig


def upsert_daily_telemetry(data: dict) -> bool:
    """UPSERT into daily_telemetry table based on date."""
    try:
        today = str(datetime.now().date())
        data["date"] = today

        # Check if exists
        existing = get_todays_telemetry()

        if existing:
            # UPDATE
            supabase.table("daily_telemetry").update(data).eq("date", today).execute()
        else:
            # INSERT
            supabase.table("daily_telemetry").insert(data).execute()

        return True
    except Exception as e:
        st.error(f"UPSERT error (daily_telemetry): {e}")
        return False


def upsert_tape_measurements(data: dict) -> bool:
    """UPSERT into tape_measurements table based on date."""
    try:
        today = str(datetime.now().date())
        data["date"] = today

        # Check if exists
        existing = get_todays_tape_measurements()

        if existing:
            # UPDATE
            supabase.table("tape_measurements").update(data).eq("date", today).execute()
        else:
            # INSERT
            supabase.table("tape_measurements").insert(data).execute()

        return True
    except Exception as e:
        st.error(f"UPSERT error (tape_measurements): {e}")
        return False


# ============================================================================
# HISTORICAL TREND GRAPH (Top, Full Width)
# ============================================================================

st.subheader("📈 Historical Trends")
last_30_days = get_last_30_days()
if not last_30_days.empty:
    fig_trend = create_trend_graph(last_30_days)
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Not enough historical data yet. Start logging to see trends.")

st.divider()

# ============================================================================
# MAIN LAYOUT: LEFT COLUMN (Completed Today) + RIGHT COLUMN (Input Forms)
# ============================================================================

col_completed, col_input = st.columns([1, 2.5])

# ========================================================================
# LEFT COLUMN: COMPLETED TODAY
# ========================================================================

with col_completed:
    st.subheader("✓ Completed Today")

    today_telemetry = get_todays_telemetry()
    today_tape = get_todays_tape_measurements()

    # Daily Telemetry Section
    st.write("**Daily Telemetry**")

    if today_telemetry:
        weight_val = today_telemetry.get("daily_weight")
        sleep_val = today_telemetry.get("sleep_hrs")
        rhr_val = today_telemetry.get("rhr")

        if weight_val is not None:
            st.caption(f"✓ Morning Weight: {weight_val} kg")
        else:
            st.caption("⏳ Morning Weight: Not Logged")

        if sleep_val is not None:
            st.caption(f"✓ Sleep: {sleep_val} hrs")
        else:
            st.caption("⏳ Sleep: Not Logged")

        if rhr_val is not None:
            st.caption(f"✓ RHR: {rhr_val} bpm")
        else:
            st.caption("⏳ RHR: Not Logged")
    else:
        st.caption("⏳ Daily Telemetry: Not Logged")

    st.divider()

    # Tape Measurements Section
    st.write("**Tape Measurements**")

    if today_tape:
        waist_val = today_tape.get("waist")
        if waist_val is not None:
            st.caption(f"✓ Measurements Logged")
        else:
            st.caption("⏳ Tape Measurements: Not Logged")
    else:
        st.caption("⏳ Tape Measurements: Not Logged")

# ========================================================================
# RIGHT COLUMN: INPUT FORMS
# ========================================================================

with col_input:
    st.subheader("📝 Input Data")

    # ====================================================================
    # DAILY TELEMETRY SECTION
    # ====================================================================

    st.write("**Daily Telemetry**")

    col1, col2 = st.columns(2)
    with col1:
        daily_weight = st.number_input(
            "Morning Weight (kg)", step=0.05, value=0.0, key="weight_input"
        )
        sleep_hrs = st.number_input(
            "Sleep Duration (hrs)", step=0.5, value=0.0, key="sleep_input"
        )
    with col2:
        rhr = st.number_input(
            "Resting Heart Rate (bpm)", step=1, value=0, key="rhr_input"
        )

    st.write("**Discomfort Scales**")

    col1, col2 = st.columns(2)
    with col1:
        shoulder_pain = st.slider(
            "Shoulder Discomfort", 0, 10, 0, key="shoulder_slider"
        )
        elbow_pain = st.slider("Elbow Discomfort", 0, 10, 0, key="elbow_slider")
    with col2:
        wrist_pain = st.slider("Wrist Discomfort", 0, 10, 0, key="wrist_slider")
        lower_back_pain = st.slider(
            "Lower Back Discomfort", 0, 10, 0, key="back_slider"
        )

    pain_note = st.text_area("Pain Notes", value="", key="pain_notes_input")

    # Stage Daily Telemetry button
    if st.button("📌 Stage Daily Telemetry", use_container_width=True):
        st.session_state.pending_checkin["daily_telemetry"] = {
            "daily_weight": daily_weight if daily_weight > 0 else None,
            "sleep_hrs": sleep_hrs if sleep_hrs > 0 else None,
            "rhr": rhr if rhr > 0 else None,
            "shoulder_pain": shoulder_pain,
            "elbow_pain": elbow_pain,
            "wrist_pain": wrist_pain,
            "lower_back_pain": lower_back_pain,
            "pain_notes": pain_note if pain_note else None,
        }
        st.toast("✓ Daily telemetry staged!")

    st.divider()

    # ====================================================================
    # TAPE MEASUREMENTS SECTION (Hidden in Expander)
    # ====================================================================

    with st.expander("📏 Bi-Weekly Tape Measurements"):
        col1, col2 = st.columns(2)
        with col1:
            waist = st.number_input(
                "Waist (cm)", step=0.5, value=0.0, key="waist_input"
            )
            shoulders = st.number_input(
                "Shoulders (cm)", step=0.5, value=0.0, key="shoulders_input"
            )
            chest = st.number_input(
                "Chest (cm)", step=0.5, value=0.0, key="chest_input"
            )
        with col2:
            arms = st.number_input("Arms (cm)", step=0.5, value=0.0, key="arms_input")
            legs = st.number_input("Legs (cm)", step=0.5, value=0.0, key="legs_input")

        # Stage Tape Measurements button
        if st.button("📌 Stage Tape Measurements", use_container_width=True):
            st.session_state.pending_checkin["tape_measurements"] = {
                "waist": waist if waist > 0 else None,
                "shoulders": shoulders if shoulders > 0 else None,
                "chest": chest if chest > 0 else None,
                "arms": arms if arms > 0 else None,
                "legs": legs if legs > 0 else None,
            }
            st.toast("✓ Tape measurements staged!")

# ============================================================================
# PENDING CHECKIN DISPLAY & COMMIT BUTTON (Bottom, Full Width)
# ============================================================================

st.divider()
st.subheader("🛒 Pending Check-In")

if st.session_state.pending_checkin:
    # Show staged data
    for section, data in st.session_state.pending_checkin.items():
        st.write(f"**{section.replace('_', ' ').title()}**")
        st.json(data)

    st.divider()

    # Master Commit button
    if st.button("✓ Commit Daily Check-In", type="primary", use_container_width=True):
        with st.spinner("Committing check-in data..."):
            try:
                success = True

                # UPSERT daily telemetry if staged
                if "daily_telemetry" in st.session_state.pending_checkin:
                    if not upsert_daily_telemetry(
                        st.session_state.pending_checkin["daily_telemetry"]
                    ):
                        success = False

                # UPSERT tape measurements if staged
                if "tape_measurements" in st.session_state.pending_checkin:
                    if not upsert_tape_measurements(
                        st.session_state.pending_checkin["tape_measurements"]
                    ):
                        success = False

                if success:
                    st.success("🎉 Check-In committed successfully!")
                    st.session_state.pending_checkin = {}
                    st.rerun()
                else:
                    st.error("Failed to commit some data.")

            except Exception as e:
                st.error(f"Commit error: {e}")

else:
    st.caption(
        "_No data staged yet. Use the 'Stage' buttons above to prepare your check-in data._"
    )
