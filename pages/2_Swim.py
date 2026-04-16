"""
Pages: Swim - Cardiovascular Capacity Logging (Session-Based, Widget Grid)
Advanced session builder mirroring 1_Gym.py with explicit number_input widgets, state management, and historical context.
Schema: Parent (swim_logs: log_id UUID, date, swim_type, stroke_type) -> Child (swim_sets: set_id UUID, log_id FK, set_number, distance_m, duration_min, pace)
Features:
  - Session-based "shopping cart" workflow (pending_swim list)
  - Dynamic widget grid with Add/Remove set buttons
  - Careful key management to avoid duplicate key errors
  - Historical performance display per stroke
  - Completed today tracking
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database import supabase

# ============================================================================
# PAGE CONFIG & STATE INITIALIZATION
# ============================================================================

st.set_page_config(page_title="Swim - Protocol Telemetry", layout="wide")
st.header("Cardiovascular Capacity")

# Initialize session state variables
if "pending_swim" not in st.session_state:
    st.session_state.pending_swim = []

if "current_stroke" not in st.session_state:
    st.session_state.current_stroke = None

if "num_swim_sets" not in st.session_state:
    st.session_state.num_swim_sets = 3


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_stroke_options() -> list:
    """Return list of available stroke types."""
    return ["Freestyle", "Breaststroke", "Backstroke", "Butterfly"]


def get_previous_performance(stroke_type: str) -> pd.DataFrame:
    """Query Supabase for most recent performance of given stroke type."""
    try:
        # Get most recent swim log for this stroke
        swim_resp = (
            supabase.table("swim_logs")
            .select("log_id, date, stroke_type")
            .eq("stroke_type", stroke_type)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )

        if not swim_resp.data:
            return pd.DataFrame()

        log_id = swim_resp.data[0]["log_id"]

        # Get sets for this log
        sets_resp = (
            supabase.table("swim_sets")
            .select("set_number, distance_m, duration_min, pace")
            .eq("log_id", log_id)
            .order("set_number")
            .execute()
        )

        if sets_resp.data:
            df = pd.DataFrame(sets_resp.data)
            df = df[["set_number", "distance_m", "duration_min", "pace"]]
            df.columns = ["Set", "Distance (m)", "Duration (min)", "Pace (min/m)"]
            return df
        return pd.DataFrame()

    except Exception as e:
        st.warning(f"Error fetching history: {e}")
        return pd.DataFrame()


def get_completed_today() -> list:
    """Query Supabase for swim_logs entries for today."""
    try:
        today = str(datetime.now().date())
        resp = (
            supabase.table("swim_logs")
            .select("stroke_type, swim_type")
            .eq("date", today)
            .execute()
        )

        if resp.data:
            return [f"• {item['stroke_type']} ({item['swim_type']})" for item in resp.data]
        return []

    except Exception as e:
        st.warning(f"Error fetching completed swims: {e}")
        return []


def collect_current_grid_values(stroke_type: str, num_sets: int) -> pd.DataFrame:
    """
    Collect values from the dynamically generated number_input grid.
    Keys are formatted as: {metric}_{stroke_type}_{index}
    Pace is calculated as duration_min / distance_m
    """
    data = []
    for i in range(num_sets):
        distance = st.session_state.get(f"dist_{stroke_type}_{i}", 0.0)
        duration = st.session_state.get(f"duration_{stroke_type}_{i}", 0.0)

        # Calculate pace (minutes per meter)
        pace = duration / distance if distance > 0 else 0.0

        # Only include rows with meaningful data
        if distance > 0 or duration > 0:
            data.append({
                "Set": i + 1,
                "Distance (m)": distance,
                "Duration (min)": duration,
                "Pace (min/m)": round(pace, 3),
            })

    return pd.DataFrame(data)


def insert_pending_swim() -> bool:
    """Batch insert all pending swim sessions to Supabase (Parent -> Child)."""
    try:
        today = str(datetime.now().date())

        for swim_data in st.session_state.pending_swim:
            
            # Calculate total distance
            df = swim_data["sets_df"]
            total_dist = float(df["Distance (m)"].sum())
            # Insert parent record (swim_logs) with UUID log_id
            parent_data = {
                "date": today,
                "swim_type": swim_data["swim_type"],
                "stroke_type": swim_data["stroke_type"],
                "total_distance_m": total_dist,
            }
            parent_resp = supabase.table("swim_logs").insert(parent_data).execute()

            if parent_resp.data:
                log_id = parent_resp.data[0]["log_id"]

                # Prepare and insert child records (swim_sets)
                child_data = [
                    {
                        "log_id": log_id,
                        "set_number": int(row["Set"]),
                        "distance_m": float(row["Distance (m)"]),
                        "duration_min": float(row["Duration (min)"]),
                        "pace": float(row["Pace (min/m)"]),
                    }
                    for _, row in swim_data["sets_df"].iterrows()
                ]

                if child_data:
                    supabase.table("swim_sets").insert(child_data).execute()

        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False


# ============================================================================
# REST DAY LOGIC (Top of Page)
# ============================================================================

col_rest_toggle, col_spacer = st.columns([1, 3])

with col_rest_toggle:
    is_swim_rest = st.checkbox("No Swimming Today")

if is_swim_rest:
    st.info("✓ Central nervous system recovery logged.")

    if st.button("Log Swim Rest Day", type="primary"):
        today = str(datetime.now().date())
        parent_data = {
            "date": today,
            "swim_type": "Rest",
            "stroke_type": "None",
        }

        response = supabase.table("swim_logs").insert(parent_data).execute()
        if response.data:
            st.success("Swim rest day logged successfully!")
            st.session_state.pending_swim = []
        else:
            st.error("Failed to log rest day.")

else:
    # ========================================================================
    # ACTIVE SWIM SESSION
    # ========================================================================

    st.divider()

    # LAYOUT: Completed Today (side) + Session Builder (main)
    col_completed, col_main = st.columns([1, 3])

    with col_completed:
        st.subheader("✓ Completed Today")
        completed = get_completed_today()
        if completed:
            for swim in completed:
                st.caption(swim)
        else:
            st.caption("_No swims logged yet_")

    with col_main:
        # ====================================================================
        # STEP 1: SWIM TYPE & STROKE SELECTION
        # ====================================================================

        st.subheader("📋 Session Builder")

        col1, col2 = st.columns(2)
        with col1:
            # Swim type selector
            swim_type = st.selectbox(
                "Swim Type",
                ["Endurance", "Sprints"],
                key="swim_type_select"
            )
        with col2:
            # Stroke selector
            stroke_options = get_stroke_options()
            stroke_type = st.selectbox(
                "Stroke",
                stroke_options,
                key="stroke_select"
            )

        # Reset grid state when stroke changes
        if stroke_type != st.session_state.current_stroke:
            st.session_state.current_stroke = stroke_type
            st.session_state.num_swim_sets = 2
            st.rerun()

        st.divider()

        # ====================================================================
        # PREVIOUS PERFORMANCE (Read-only)
        # ====================================================================

        st.subheader("📊 Previous Performance")
        history_df = get_previous_performance(stroke_type)

        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
            st.caption("_No previous history found for this stroke_")

        st.divider()

        # ====================================================================
        # STEP 2: DYNAMIC WIDGET GRID
        # ====================================================================

        st.subheader("⚙️ Input Sets")

        # Header row for the grid
        col_set, col_distance, col_duration, col_pace = st.columns(4)
        with col_set:
            st.write("**Set**")
        with col_distance:
            st.write("**Distance (m)**")
        with col_duration:
            st.write("**Duration (min)**")
        with col_pace:
            st.write("**Pace (min/m)**")

        # Dynamic rows with number inputs
        # Key format: {metric}_{stroke_type}_{index} to avoid collisions
        for i in range(st.session_state.num_swim_sets):
            col_set, col_distance, col_duration, col_pace = st.columns(4)

            with col_set:
                st.write(f"Set {i + 1}")

            with col_distance:
                st.number_input(
                    "Distance (m)",
                    min_value=0.0,
                    step=25.0,
                    value=0.0,
                    key=f"dist_{stroke_type}_{i}",
                    label_visibility="collapsed",
                )

            with col_duration:
                st.number_input(
                    "Duration (min)",
                    min_value=0.0,
                    step=1.0,
                    value=0.0,
                    key=f"duration_{stroke_type}_{i}",
                    label_visibility="collapsed",
                )

            with col_pace:
                # Read-only pace display (calculated)
                dist_val = st.session_state.get(f"dist_{stroke_type}_{i}", 0.0)
                dur_val = st.session_state.get(f"duration_{stroke_type}_{i}", 0.0)
                pace_val = dur_val / dist_val if dist_val > 0 else 0.0
                st.metric("Pace", f"{pace_val:.3f}" if pace_val > 0 else "—")

        # Add/Remove set buttons
        col_add, col_remove = st.columns(2)

        with col_add:
            if st.button("➕ Add Set", use_container_width=True):
                st.session_state.num_swim_sets += 1
                st.rerun()

        with col_remove:
            if st.button("➖ Remove Last Set", use_container_width=True):
                if st.session_state.num_swim_sets > 1:
                    st.session_state.num_swim_sets -= 1
                    st.rerun()

        st.divider()

        # ====================================================================
        # LOG SWIM BUTTON
        # ====================================================================

        if st.button("📝 Log Swim", type="primary", use_container_width=True):
            # Collect grid values using carefully namespaced keys
            grid_df = collect_current_grid_values(stroke_type, st.session_state.num_swim_sets)

            if grid_df.empty:
                st.error("Please enter at least one set with distance or duration.")
            else:
                # Append to pending swim
                st.session_state.pending_swim.append({
                    "stroke_type": stroke_type,
                    "swim_type": swim_type,
                    "sets_df": grid_df,
                })

                st.success(f"✓ Added {stroke_type} to session!")

                # Reset grid for next stroke
                st.session_state.num_swim_sets = 3
                st.rerun()

    # ========================================================================
    # PENDING SWIM DISPLAY (Below main area)
    # ========================================================================

    st.divider()
    st.subheader("🛒 Pending Swim")

    if st.session_state.pending_swim:
        # Display pending swims as expandable cards
        for idx, swim_item in enumerate(st.session_state.pending_swim):
            with st.expander(
                f"✓ {swim_item['stroke_type']} ({swim_item['swim_type']}) - {len(swim_item['sets_df'])} sets"
            ):
                st.dataframe(
                    swim_item["sets_df"],
                    use_container_width=True,
                    hide_index=True,
                )

                if st.button(
                    "🗑️ Remove from Session",
                    key=f"remove_swim_{idx}",
                    use_container_width=True,
                ):
                    st.session_state.pending_swim.pop(idx)
                    st.rerun()

        st.divider()

        # Finish Session button (batch insert all pending swims)
        if st.button(
            "✓ Finish Session (Commit to Database)",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Saving swim session..."):
                if insert_pending_swim():
                    st.success(
                        f"🎉 Swim session saved! {len(st.session_state.pending_swim)} strokes committed."
                    )
                    st.session_state.pending_swim = []
                    st.session_state.current_stroke = None
                    st.session_state.num_swim_sets = 3
                    st.rerun()
                else:
                    st.error("Failed to save swim session.")

    else:
        st.caption("_No strokes added yet. Configure and log a stroke above._")
