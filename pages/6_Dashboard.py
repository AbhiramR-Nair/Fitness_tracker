"""
Pages: Dashboard - Telemetry Analytics & Forecasting (Refactored)
Central hub for data extraction, transformation, and visualization.
Auto-loading with 1:3 layout (control panel + charts) and date range filtering.
Uses new UUID-based schemas: gym_logs/exercise_sets, swim_logs/swim_sets, 
nutrition_logs, daily_telemetry.
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from database import supabase
import visualizations as viz

st.set_page_config(page_title="Dashboard - Protocol Telemetry", layout="wide")
st.header("Telemetry Dashboard")


# ============================================================================
# HELPER: DATE RANGE CALCULATION
# ============================================================================

def get_date_range(selection: str) -> tuple:
    """Calculate start_date and end_date based on selection."""
    end_date = datetime.now().date()
    if selection == "Last 30 Days":
        start_date = end_date - timedelta(days=30)
    elif selection == "Last 90 Days":
        start_date = end_date - timedelta(days=90)
    else:  # "All Time"
        start_date = datetime(2000, 1, 1).date()
    return start_date, end_date


# ============================================================================
# CACHED DATA FETCHING & TRANSFORMATION
# ============================================================================

@st.cache_data(ttl=300)
def fetch_and_transform_data(date_range_str: str) -> tuple:
    """
    Fetch data from Supabase and apply transformations & date filtering.
    Returns: (gym_df, merged_gym, swim_logs_df, swim_sets_df, nut_df, telemetry_df)
    """
    start_date, end_date = get_date_range(date_range_str)
    date_range_str_iso = f"{start_date}|{end_date}"

    with st.spinner("Fetching and processing data..."):
        # ====================================================================
        # 1. GYM DATA (gym_logs + exercise_sets)
        # ====================================================================
        try:
            gym_resp = (
                supabase.table("gym_logs")
                .select("log_id, date, workout_type, exercise")
                .gte("date", str(start_date))
                .lte("date", str(end_date))
                .execute()
            )
            gym_df = pd.DataFrame(gym_resp.data) if gym_resp.data else pd.DataFrame()

            sets_resp = supabase.table("exercise_sets").select("log_id, weight, reps, rir").execute()
            sets_df = pd.DataFrame(sets_resp.data) if sets_resp.data else pd.DataFrame()

            # Merge on log_id to create full workout dataset
            if not gym_df.empty and not sets_df.empty:
                merged_gym = pd.merge(sets_df, gym_df, on="log_id")
                merged_gym["weight"] = pd.to_numeric(merged_gym["weight"], errors="coerce")
                merged_gym["reps"] = pd.to_numeric(merged_gym["reps"], errors="coerce")
                merged_gym["tonnage"] = merged_gym["weight"] * merged_gym["reps"]
                # Brzycki 1RM Formula
                merged_gym["est_1rm"] = merged_gym.apply(
                    lambda row: (
                        row["weight"]
                        if row["reps"] == 1
                        else row["weight"] * (36 / (37 - row["reps"]))
                    ),
                    axis=1,
                )
            else:
                merged_gym = pd.DataFrame()
        except Exception as e:
            st.warning(f"Error fetching gym data: {e}")
            gym_df = pd.DataFrame()
            merged_gym = pd.DataFrame()

        # ====================================================================
        # 2. SWIM DATA (swim_logs + swim_sets)
        # ====================================================================
        try:
            swim_logs_resp = (
                supabase.table("swim_logs")
                .select("log_id, date, swim_type, stroke_type, total_distance_m")
                .gte("date", str(start_date))
                .lte("date", str(end_date))
                .execute()
            )
            swim_logs_df = pd.DataFrame(swim_logs_resp.data) if swim_logs_resp.data else pd.DataFrame()

            swim_sets_resp = supabase.table("swim_sets").select("log_id, distance_m, duration_min, pace").execute()
            swim_sets_df = pd.DataFrame(swim_sets_resp.data) if swim_sets_resp.data else pd.DataFrame()

            # Type casting
            if not swim_sets_df.empty:
                swim_sets_df["distance_m"] = pd.to_numeric(swim_sets_df["distance_m"], errors="coerce")
                swim_sets_df["duration_min"] = pd.to_numeric(swim_sets_df["duration_min"], errors="coerce")
                swim_sets_df["pace"] = pd.to_numeric(swim_sets_df["pace"], errors="coerce")
        except Exception as e:
            st.warning(f"Error fetching swim data: {e}")
            swim_logs_df = pd.DataFrame()
            swim_sets_df = pd.DataFrame()

        # ====================================================================
        # 3. NUTRITION DATA
        # ====================================================================
        try:
            nut_resp = (
                supabase.table("nutrition_logs")
                .select("date, total_calories, total_protein, total_carbs, total_fats, total_water_l")
                .gte("date", str(start_date))
                .lte("date", str(end_date))
                .order("date")
                .execute()
            )
            nut_df = pd.DataFrame(nut_resp.data) if nut_resp.data else pd.DataFrame()

            if not nut_df.empty:
                nut_df[["total_calories", "total_protein", "total_carbs", "total_fats", "total_water_l"]] = (
                    nut_df[["total_calories", "total_protein", "total_carbs", "total_fats", "total_water_l"]]
                    .apply(pd.to_numeric, errors="coerce")
                )
        except Exception as e:
            st.warning(f"Error fetching nutrition data: {e}")
            nut_df = pd.DataFrame()

        # ====================================================================
        # 4. DAILY TELEMETRY DATA (Body + Recovery consolidated)
        # ====================================================================
        try:
            telemetry_resp = (
                supabase.table("daily_telemetry")
                .select("date, daily_weight, sleep_hrs, rhr, shoulder_pain, elbow_pain, wrist_pain, lower_back_pain")
                .gte("date", str(start_date))
                .lte("date", str(end_date))
                .order("date")
                .execute()
            )
            telemetry_df = pd.DataFrame(telemetry_resp.data) if telemetry_resp.data else pd.DataFrame()

            if not telemetry_df.empty:
                telemetry_df[["daily_weight", "sleep_hrs", "rhr"]] = (
                    telemetry_df[["daily_weight", "sleep_hrs", "rhr"]]
                    .apply(pd.to_numeric, errors="coerce")
                )
        except Exception as e:
            st.warning(f"Error fetching telemetry data: {e}")
            telemetry_df = pd.DataFrame()

    return gym_df, merged_gym, swim_logs_df, swim_sets_df, nut_df, telemetry_df


# ============================================================================
# MAIN LAYOUT: CONTROL PANEL (LEFT) + CHARTS (RIGHT)
# ============================================================================

col_control, col_charts = st.columns([1, 3])

# ========================================================================
# LEFT COLUMN: CONTROL PANEL
# ========================================================================

with col_control:
    st.subheader("⚙️ Controls")

    date_range_selection = st.selectbox(
        "Date Range",
        ["Last 30 Days", "Last 90 Days", "All Time"],
        index=0,
    )

    if st.button("↻ Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption(f"📅 **Selected**: {date_range_selection}")

# ========================================================================
# RIGHT COLUMN: CHARTS & KPIs
# ========================================================================

with col_charts:
    # Fetch data with date filtering
    gym_df, merged_gym, swim_logs_df, swim_sets_df, nut_df, telemetry_df = fetch_and_transform_data(
        date_range_selection
    )

    # --- PEAK MECHANICAL OUTPUTS (KPIs) ---
    st.subheader("Peak Mechanical Outputs (Est. 1RM)")

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:
        squat_1rm = viz.get_max_1rm(merged_gym, "Smith Machine Squats")
        st.metric("Squat 1RM", squat_1rm)

    with kpi_col2:
        bench_1rm = viz.get_max_1rm(merged_gym, "Bench Press")
        st.metric("Bench 1RM", bench_1rm)

    with kpi_col3:
        deadlift_1rm = viz.get_max_1rm(merged_gym, "Deadlift")
        st.metric("Deadlift 1RM", deadlift_1rm)

    with kpi_col4:
        # Best pace from swim_sets
        if not swim_sets_df.empty and "pace" in swim_sets_df.columns:
            best_pace = swim_sets_df[swim_sets_df["pace"] > 0]["pace"].min()
            if pd.notna(best_pace):
                st.metric("Best Pace", f"{round(best_pace, 2)} min/m")
            else:
                st.metric("Best Pace", "-- min/m")
        else:
            st.metric("Best Pace", "-- min/m")

    st.divider()

    # --- ACTIVITY CONSISTENCY HEATMAP ---
    st.subheader("📊 Activity Consistency Heatmap (180 Days)")
    fig_heatmap = viz.create_consistency_heatmap(gym_df, swim_logs_df)
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown(
        """
        <div style='display: flex; justify-content: center; gap: 15px; font-size: 12px; margin-top: -10px;'>
        <div><span style='color: #1e212b;'>█</span> Rest</div>
        <div><span style='color: #ff4b4b;'>█</span> Gym</div>
        <div><span style='color: #00ffcc;'>█</span> Swim</div>
        <div><span style='color: #b042ff;'>█</span> Gym + Swim</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # --- TRAINING CONSISTENCY & SPLIT BALANCE ---
    col_tone, col_radar = st.columns([2, 1])

    with col_tone:
        st.subheader("💪 Training Consistency (Tonnage)")
        fig_tonnage = viz.create_daily_tonnage_chart(merged_gym)
        st.plotly_chart(fig_tonnage, use_container_width=True)

    with col_radar:
        st.subheader("🎯 Split Balance")
        fig_radar = viz.create_split_balance_radar(merged_gym)
        st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

    # --- BODY RECOMPOSITION FORECAST ---
    st.subheader("📈 Body Recomposition Forecast")
    fig_weight = viz.create_weight_forecast(telemetry_df)
    st.plotly_chart(fig_weight, use_container_width=True)

    st.divider()

    # --- METABOLIC & CARDIOVASCULAR TELEMETRY ---
    st.subheader("❤️ Metabolic & Cardiovascular Telemetry")

    col_cardio, col_metabolic = st.columns(2)

    with col_cardio:
        fig_cardio = viz.create_cardio_telemetry(swim_logs_df, swim_sets_df, telemetry_df)
        st.plotly_chart(fig_cardio, use_container_width=True)

    with col_metabolic:
        fig_metabolic = viz.create_metabolic_intake_chart(nut_df)
        st.plotly_chart(fig_metabolic, use_container_width=True)
