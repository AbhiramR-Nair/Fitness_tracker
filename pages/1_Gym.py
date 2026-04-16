"""
Pages: Gym - Mechanical Tension Logging (Session-Based, Widget Grid)
Advanced session builder with explicit number_input widgets, state management, and historical context.
Features:
  - Session-based "shopping cart" workflow (pending_workout list)
  - Dynamic widget grid (NOT st.data_editor) with Add/Remove set buttons
  - Careful key management to avoid duplicate key errors
  - Historical performance display
  - Completed today tracking
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database import supabase

# ============================================================================
# PAGE CONFIG & STATE INITIALIZATION
# ============================================================================

st.set_page_config(page_title="Gym - Protocol Telemetry", layout="wide")
st.header("Mechanical Tension")

# Initialize session state variables
if "pending_workout" not in st.session_state:
    st.session_state.pending_workout = []

if "current_exercise" not in st.session_state:
    st.session_state.current_exercise = None

if "num_sets" not in st.session_state:
    st.session_state.num_sets = 3


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_exercise_options(split_type: str) -> list:
    """Return list of exercises for a given split."""
    exercises = {
        "Push": [
            "Bench Press",
            "Incline DB Press",
            "Peck Deck Flyes",
            "Incline DB Flyes",
            "Lateral Raises",
            "Front Raises",
            "Shoulder Press",
            "Shoulder Shrug",
            "Cable lateral raises",
            "Overhead Tricep Extensions",
            "Rope Tricep Extensions",
            "Single arm tricep Extensions",
            "Reverse tricep extensions",
        ],
        "Pull": [
            "Deadlift",
            "Close Grip Lat Pulldown",
            "Wide Grip Lat Pulldown",
            "Seated Row",
            "Wide Grip Seated Row",
            "Hyperextensions",
            "Cable Face Pulls",
            "Reverse Pec Deck Flyes",
            "EZ Bar Curls",
            "Dumbbell Curls",
            "Hammer Curls",
            "Preacher Curls",
        ],
        "Legs": [
            "Leg Press",
            "Bulgarian Split Squats",
            "Leg Extensions",
            "Leg Curls",
            "Smith Machine Squats",
            "Abductor Machine",
            "Adductor Machine",
            "Calf Raises",
            "Sumo squats",
            "Hip Thrusts",
        ],
        "Core/Abs": [
            "Ab Crunches",
            "Hanging Leg Raises",
            "Ab crunch machine",
            "Sit-ups",
            "Russian Twists",
            "Heel Touches",
        ],
        "Forearms/Grip": [
            "Wrist Curls",
            "Reverse Wrist Curls",
            "Natural Forearm Curls",
            "Natural Reverse Forearm Curls",
        ],
    }
    return exercises.get(split_type, [])


def get_previous_performance(exercise_name: str) -> pd.DataFrame:
    """Query Supabase for most recent performance of given exercise."""
    try:
        gym_resp = (
            supabase.table("gym_logs")
            .select("log_id, date, exercise")
            .eq("exercise", exercise_name)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )

        if not gym_resp.data:
            return pd.DataFrame()

        log_id = gym_resp.data[0]["log_id"]

        sets_resp = (
            supabase.table("exercise_sets")
            .select("set_number, weight, reps, rir")
            .eq("log_id", log_id)
            .order("set_number")
            .execute()
        )

        if sets_resp.data:
            df = pd.DataFrame(sets_resp.data)
            df = df[["set_number", "weight", "reps", "rir"]]
            df.columns = ["Set", "Weight (kg)", "Reps", "RIR"]
            return df
        return pd.DataFrame()

    except Exception as e:
        st.warning(f"Error fetching history: {e}")
        return pd.DataFrame()


def get_completed_today() -> list:
    """Query Supabase for gym_logs entries for today."""
    try:
        today = str(datetime.now().date())
        resp = (
            supabase.table("gym_logs")
            .select("exercise, workout_type")
            .eq("date", today)
            .execute()
        )

        if resp.data:
            return [f"• {item['exercise']} ({item['workout_type']})" for item in resp.data]
        return []

    except Exception as e:
        st.warning(f"Error fetching completed exercises: {e}")
        return []


def collect_current_grid_values(exercise_name: str, num_sets: int) -> pd.DataFrame:
    """
    Collect values from the dynamically generated number_input grid.
    Keys are formatted as: {metric}_{exercise}_{index}
    """
    data = []
    for i in range(num_sets):
        weight = st.session_state.get(f"weight_{exercise_name}_{i}", 0.0)
        reps = st.session_state.get(f"reps_{exercise_name}_{i}", 0)
        rir = st.session_state.get(f"rir_{exercise_name}_{i}", 0)

        # Only include rows with meaningful data
        if weight > 0 or reps > 0:
            data.append({
                "Set": i + 1,
                "Weight (kg)": weight,
                "Reps": reps,
                "RIR": rir,
            })

    return pd.DataFrame(data)


def insert_pending_workout() -> bool:
    """Batch insert all pending workout exercises to Supabase (Parent -> Child)."""
    try:
        today = str(datetime.now().date())

        for exercise_data in st.session_state.pending_workout:
            # Insert parent record (gym_logs)
            parent_data = {
                "date": today,
                "workout_type": exercise_data["workout_type"],
                "exercise": exercise_data["exercise"],
            }
            parent_resp = supabase.table("gym_logs").insert(parent_data).execute()

            if parent_resp.data:
                log_id = parent_resp.data[0]["log_id"]

                # Prepare and insert child records (exercise_sets)
                child_data = [
                    {
                        "log_id": log_id,
                        "set_number": int(row["Set"]),
                        "weight": float(row["Weight (kg)"]),
                        "reps": int(row["Reps"]),
                        "rir": int(row["RIR"]),
                    }
                    for _, row in exercise_data["sets_df"].iterrows()
                ]

                if child_data:
                    supabase.table("exercise_sets").insert(child_data).execute()

        return True

    except Exception as e:
        st.error(f"Database error: {e}")
        return False


# ============================================================================
# REST DAY LOGIC (Top of Page)
# ============================================================================

col_rest_toggle, col_spacer = st.columns([1, 3])

with col_rest_toggle:
    is_rest_day = st.checkbox("Today is a Rest Day")

if is_rest_day:
    st.info("✓ Enjoy the recovery. Muscular repair happens today.")

    if st.button("Log Gym Rest Day", type="primary"):
        today = str(datetime.now().date())
        parent_data = {
            "date": today,
            "workout_type": "Rest",
            "exercise": "None",
        }

        response = supabase.table("gym_logs").insert(parent_data).execute()
        if response.data:
            st.success("Rest day logged successfully!")
            st.session_state.pending_workout = []
        else:
            st.error("Failed to log rest day.")

else:
    # ========================================================================
    # ACTIVE WORKOUT SESSION
    # ========================================================================

    st.divider()

    # LAYOUT: Completed Today (side) + Session Builder (main)
    col_completed, col_main = st.columns([1, 3])

    with col_completed:
        st.subheader("✓ Completed Today")
        completed = get_completed_today()
        if completed:
            for exercise in completed:
                st.caption(exercise)
        else:
            st.caption("_No exercises logged yet_")

    with col_main:
        # ====================================================================
        # STEP 1: SPLIT & EXERCISE SELECTION
        # ====================================================================

        st.subheader("📋 Session Builder")

        col1, col2 = st.columns(2)
        with col1:
            # Split selector
            workout_type = st.selectbox(
                "Split",
                ["Push", "Pull", "Legs", "Core/Abs", "Forearms/Grip"]
            )
        with col2:
            # Exercise selector
            exercise_options = get_exercise_options(workout_type)
            exercise = st.selectbox(
                "Exercise",
                exercise_options,
                key="exercise_select"
            )

        # Reset grid state when exercise changes
        if exercise != st.session_state.current_exercise:
            st.session_state.current_exercise = exercise
            st.session_state.num_sets = 3
            st.rerun()

        st.divider()

        # ====================================================================
        # PREVIOUS PERFORMANCE (Read-only)
        # ====================================================================

        st.subheader("📊 Previous Performance")
        history_df = get_previous_performance(exercise)

        if not history_df.empty:
            st.dataframe(history_df, use_container_width=True, hide_index=True)
        else:
            st.caption("_No previous history found for this exercise_")

        st.divider()

        # ====================================================================
        # STEP 2: DYNAMIC WIDGET GRID
        # ====================================================================

        st.subheader("⚙️ Input Sets")

        # Header row for the grid
        col_set, col_weight, col_reps, col_rir = st.columns(4)
        with col_set:
            st.write("**Set**")
        with col_weight:
            st.write("**Weight (kg)**")
        with col_reps:
            st.write("**Reps**")
        with col_rir:
            st.write("**RIR**")

        # Dynamic rows with number inputs
        # Key format: {metric}_{exercise}_{index} to avoid collisions
        for i in range(st.session_state.num_sets):
            col_set, col_weight, col_reps, col_rir = st.columns(4)

            with col_set:
                st.write(f"Set {i + 1}")

            with col_weight:
                st.number_input(
                    "Weight (kg)",
                    min_value=0.0,
                    step=0.5,
                    value=0.0,
                    key=f"weight_{exercise}_{i}",
                    label_visibility="collapsed",
                )

            with col_reps:
                st.number_input(
                    "Reps",
                    min_value=0,
                    max_value=100,
                    step=1,
                    value=0,
                    key=f"reps_{exercise}_{i}",
                    label_visibility="collapsed",
                )

            with col_rir:
                st.number_input(
                    "RIR",
                    min_value=0,
                    max_value=10,
                    step=1,
                    value=0,
                    key=f"rir_{exercise}_{i}",
                    label_visibility="collapsed",
                )

        # Add/Remove set buttons
        col_add, col_remove = st.columns(2)

        with col_add:
            if st.button("➕ Add Set", use_container_width=True):
                st.session_state.num_sets += 1
                st.rerun()

        with col_remove:
            if st.button("➖ Remove Last Set", use_container_width=True):
                if st.session_state.num_sets > 1:
                    st.session_state.num_sets -= 1
                    st.rerun()

        st.divider()

        # ====================================================================
        # LOG EXERCISE BUTTON
        # ====================================================================

        if st.button("📝 Log Exercise", type="primary", use_container_width=True):
            # Collect grid values using carefully namespaced keys
            grid_df = collect_current_grid_values(exercise, st.session_state.num_sets)

            if grid_df.empty:
                st.error("Please enter at least one set with weight or reps.")
            else:
                # Append to pending workout
                st.session_state.pending_workout.append({
                    "exercise": exercise,
                    "workout_type": workout_type,
                    "sets_df": grid_df,
                })

                st.success(f"✓ Added {exercise} to session!")

                # Reset grid for next exercise
                st.session_state.num_sets = 3
                st.rerun()

    # ========================================================================
    # PENDING WORKOUT DISPLAY (Below main area)
    # ========================================================================

    st.divider()
    st.subheader("🛒 Pending Workout")

    if st.session_state.pending_workout:
        # Display pending exercises as expandable cards
        for idx, exercise_item in enumerate(st.session_state.pending_workout):
            with st.expander(
                f"✓ {exercise_item['exercise']} ({exercise_item['workout_type']}) - {len(exercise_item['sets_df'])} sets"
            ):
                st.dataframe(
                    exercise_item["sets_df"],
                    use_container_width=True,
                    hide_index=True,
                )

                if st.button(
                    "🗑️ Remove from Session",
                    key=f"remove_{idx}",
                    use_container_width=True,
                ):
                    st.session_state.pending_workout.pop(idx)
                    st.rerun()

        st.divider()

        # Finish Session button (batch insert all pending exercises)
        if st.button(
            "✓ Finish Session (Commit to Database)",
            type="primary",
            use_container_width=True,
        ):
            with st.spinner("Saving workout..."):
                if insert_pending_workout():
                    st.success(
                        f"🎉 Workout saved! {len(st.session_state.pending_workout)} exercises committed."
                    )
                    st.session_state.pending_workout = []
                    st.session_state.current_exercise = None
                    st.session_state.num_sets = 3
                    st.rerun()
                else:
                    st.error("Failed to save workout.")

    else:
        st.caption("_No exercises added yet. Configure and log an exercise above._")
