"""
Pages: Nutrition - Biochemical Inputs Logging (Session-Based, UPSERT)
Advanced meal builder with parent/child relational schema, UPSERT logic, and macro tracking.
Schema: Parent (nutrition_logs: log_id UUID, date UNIQUE, total_calories, total_protein, total_carbs, total_fats, total_water_l)
        -> Child (meal_entries: entry_id UUID, log_id FK, meal_name, food_item, calories, protein, carbs, fats, water_l)
Features:
  - Session-based pending_meals cart ("Shopping Cart" workflow)
  - Quick Add meal presets with auto-fill
  - UPSERT logic: UPDATE existing daily log OR INSERT new one
  - Remaining macros tracker with daily targets
  - Editable macro inputs before committing
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from database import supabase

# ============================================================================
# PAGE CONFIG & CONSTANTS
# ============================================================================

st.set_page_config(page_title="Nutrition - Protocol Telemetry", layout="wide")
st.header("Biochemical Inputs")

# Daily Macro Targets
DAILY_TARGETS = {
    "calories": 3000,
    "protein": 160,
    "carbs": 350,
    "fats": 80,
    "water": 4.0,
}

# ============================================================================
# STATE INITIALIZATION
# ============================================================================

if "pending_meals" not in st.session_state:
    st.session_state.pending_meals = []


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def define_quick_add_meals() -> dict:
    """Return dictionary of preset meals with macro values."""
    return {
        "Custom Entry": {"calories": 0, "protein": 0, "carbs": 0, "fats": 0, "water": 0},
        "Protein Oats": {"calories": 350, "protein": 15, "carbs": 52, "fats": 8, "water": 0.3},
        "Whole Boiled Eggs (2)": {"calories": 155, "protein": 13, "carbs": 1, "fats": 11, "water": 0.1},
        "Grilled Chicken Breast (150g)": {"calories": 240, "protein": 45, "carbs": 0, "fats": 5, "water": 0.2},
        "Brown Rice (150g cooked)": {"calories": 195, "protein": 5, "carbs": 43, "fats": 2, "water": 0.15},
        "Salmon Fillet (150g)": {"calories": 280, "protein": 32, "carbs": 0, "fats": 16, "water": 0.2},
        "Banana": {"calories": 105, "protein": 1, "carbs": 27, "fats": 0, "water": 0.2},
        "Greek Yogurt (200g)": {"calories": 130, "protein": 18, "carbs": 9, "fats": 3, "water": 0.15},
        "Whey Protein Shake": {"calories": 120, "protein": 25, "carbs": 2, "fats": 1, "water": 0.3},
    }

def update_macro_inputs():
    """Callback to force macro inputs to update when quick add selection changes."""
    # 1. Get selected quick add meal
    selected_meal = st.session_state.quick_add_select
    
    # 2. Get preset values
    preset = define_quick_add_meals()[selected_meal]
    
    # 3. Update macro inputs
    st.session_state.cal_input = int(preset["calories"])
    st.session_state.pro_input = int(preset["protein"])
    st.session_state.carb_input = int(preset["carbs"])
    st.session_state.fat_input = int(preset["fats"])
    st.session_state.water_input = float(preset["water"])


def get_todays_nutrition() -> dict:
    """Query Supabase for today's nutrition_logs entry (if exists)."""
    try:
        today = str(datetime.now().date())
        resp = (
            supabase.table("nutrition_logs")
            .select("log_id, total_calories, total_protein, total_carbs, total_fats, total_water_l")
            .eq("date", today)
            .execute()
        )

        if resp.data:
            return resp.data[0]
        return None

    except Exception as e:
        st.warning(f"Error fetching daily nutrition: {e}")
        return None


def calculate_pending_totals() -> dict:
    """Calculate total macros from pending_meals."""
    if not st.session_state.pending_meals:
        return {
            "calories": 0,
            "protein": 0,
            "carbs": 0,
            "fats": 0,
            "water": 0,
        }

    totals = {
        "calories": sum(m.get("calories", 0) for m in st.session_state.pending_meals),
        "protein": sum(m.get("protein", 0) for m in st.session_state.pending_meals),
        "carbs": sum(m.get("carbs", 0) for m in st.session_state.pending_meals),
        "fats": sum(m.get("fats", 0) for m in st.session_state.pending_meals),
        "water": sum(m.get("water", 0) for m in st.session_state.pending_meals),
    }
    return totals


def calculate_remaining_macros() -> dict:
    """Calculate remaining macros based on daily targets and consumed amounts."""
    today_nutrition = get_todays_nutrition()

    # Start with committed totals
    consumed = {
        "calories": today_nutrition.get("total_calories", 0) if today_nutrition else 0,
        "protein": today_nutrition.get("total_protein", 0) if today_nutrition else 0,
        "carbs": today_nutrition.get("total_carbs", 0) if today_nutrition else 0,
        "fats": today_nutrition.get("total_fats", 0) if today_nutrition else 0,
        "water": today_nutrition.get("total_water_l", 0) if today_nutrition else 0,
    }

    # Add pending meals
    pending_totals = calculate_pending_totals()
    for key in consumed:
        consumed[key] += pending_totals[key]

    # Calculate remaining
    remaining = {
        "calories": max(0, DAILY_TARGETS["calories"] - consumed["calories"]),
        "protein": max(0, DAILY_TARGETS["protein"] - consumed["protein"]),
        "carbs": max(0, DAILY_TARGETS["carbs"] - consumed["carbs"]),
        "fats": max(0, DAILY_TARGETS["fats"] - consumed["fats"]),
        "water": max(0, DAILY_TARGETS["water"] - consumed["water"]),
    }

    return {
        "consumed": consumed,
        "remaining": remaining,
        "goals_reached": {
            "calories": consumed["calories"] >= DAILY_TARGETS["calories"],
            "protein": consumed["protein"] >= DAILY_TARGETS["protein"],
            "carbs": consumed["carbs"] >= DAILY_TARGETS["carbs"],
            "fats": consumed["fats"] >= DAILY_TARGETS["fats"],
            "water": consumed["water"] >= DAILY_TARGETS["water"],
        },
    }


def upsert_nutrition_logs(log_id: str = None, delta_macros: dict = None) -> bool:
    """
    UPSERT nutrition_logs for today.
    If log_id exists, UPDATE totals by adding delta_macros.
    If not, INSERT new record with delta_macros as initial values.
    """
    try:
        today = str(datetime.now().date())

        if delta_macros is None:
            delta_macros = {"calories": 0, "protein": 0, "carbs": 0, "fats": 0, "water": 0}

        if log_id:
            # UPDATE existing record
            update_data = {
                "total_calories": ("total_calories", delta_macros["calories"]),
                "total_protein": ("total_protein", delta_macros["protein"]),
                "total_carbs": ("total_carbs", delta_macros["carbs"]),
                "total_fats": ("total_fats", delta_macros["fats"]),
                "total_water_l": ("total_water_l", delta_macros["water"]),
            }

            # Use Supabase raw SQL for atomic math operations
            # Since supabase-py doesn't support native increment, we fetch and update
            current = (
                supabase.table("nutrition_logs")
                .select("total_calories, total_protein, total_carbs, total_fats, total_water_l")
                .eq("log_id", log_id)
                .execute()
            )

            if current.data:
                new_totals = {
                    "total_calories": current.data[0]["total_calories"] + delta_macros["calories"],
                    "total_protein": current.data[0]["total_protein"] + delta_macros["protein"],
                    "total_carbs": current.data[0]["total_carbs"] + delta_macros["carbs"],
                    "total_fats": current.data[0]["total_fats"] + delta_macros["fats"],
                    "total_water_l": current.data[0]["total_water_l"] + delta_macros["water"],
                }

                supabase.table("nutrition_logs").update(new_totals).eq("log_id", log_id).execute()
                return log_id
        else:
            # INSERT new record
            insert_data = {
                "date": today,
                "total_calories": delta_macros["calories"],
                "total_protein": delta_macros["protein"],
                "total_carbs": delta_macros["carbs"],
                "total_fats": delta_macros["fats"],
                "total_water_l": delta_macros["water"],
            }

            resp = supabase.table("nutrition_logs").insert(insert_data).execute()

            if resp.data:
                return resp.data[0]["log_id"]
        return None

    except Exception as e:
        st.error(f"UPSERT error: {e}")
        return None


def insert_meal_entries(log_id: str) -> bool:
    """Batch insert all pending meals into meal_entries table."""
    try:
        if not st.session_state.pending_meals:
            return True

        today = str(datetime.now().date())
        meal_data = [
            {
                "log_id": log_id,
                "meal_name": meal.get("meal_name"),
                "food_item": meal.get("food_item"),
                "calories": float(meal.get("calories", 0)),
                "protein": float(meal.get("protein", 0)),
                "carbs": float(meal.get("carbs", 0)),
                "fats": float(meal.get("fats", 0)),
                "water_l": float(meal.get("water", 0)),
            }
            for meal in st.session_state.pending_meals
        ]

        supabase.table("meal_entries").insert(meal_data).execute()
        return True

    except Exception as e:
        st.error(f"Failed to insert meal entries: {e}")
        return False


# ============================================================================
# MAIN LAYOUT: LEFT COLUMN (Remaining Macros) + RIGHT COLUMN (Meal Builder)
# ============================================================================

col_remaining, col_builder = st.columns([1, 3])

# ========================================================================
# LEFT COLUMN: REMAINING MACROS TRACKER
# ========================================================================

with col_remaining:
    st.subheader("📊 Daily Goals")

    # Calculate remaining macros
    macro_data = calculate_remaining_macros()
    consumed = macro_data["consumed"]
    remaining = macro_data["remaining"]
    goals_reached = macro_data["goals_reached"]

    # Display metrics
    st.write("**Targets**")
    st.caption(f"Calories: {DAILY_TARGETS['calories']}")
    st.caption(f"Protein: {DAILY_TARGETS['protein']}g")
    st.caption(f"Carbs: {DAILY_TARGETS['carbs']}g")
    st.caption(f"Fats: {DAILY_TARGETS['fats']}g")
    st.caption(f"Water: {DAILY_TARGETS['water']}L")

    st.divider()
    st.write("**Remaining**")

    # Calories
    cal_color = "🟢" if remaining["calories"] > 0 else "🔴"
    st.metric(
        f"{cal_color} Calories",
        f"{int(remaining['calories'])} kcal",
        f"Consumed: {int(consumed['calories'])}",
    )

    # Protein
    pro_color = "🟢" if remaining["protein"] > 0 else "🔴"
    st.metric(
        f"{pro_color} Protein",
        f"{remaining['protein']:.0f}g",
        f"Consumed: {consumed['protein']:.0f}g",
    )

    # Carbs
    carb_color = "🟢" if remaining["carbs"] > 0 else "🔴"
    st.metric(
        f"{carb_color} Carbs",
        f"{remaining['carbs']:.0f}g",
        f"Consumed: {consumed['carbs']:.0f}g",
    )

    # Fats
    fat_color = "🟢" if remaining["fats"] > 0 else "🔴"
    st.metric(
        f"{fat_color} Fats",
        f"{remaining['fats']:.0f}g",
        f"Consumed: {consumed['fats']:.0f}g",
    )

    # Water
    water_color = "🟢" if remaining["water"] > 0 else "🔴"
    st.metric(
        f"{water_color} Water",
        f"{remaining['water']:.1f}L",
        f"Consumed: {consumed['water']:.1f}L",
    )

# ========================================================================
# RIGHT COLUMN: MEAL BUILDER
# ========================================================================

with col_builder:
    st.subheader("🍽️ Meal Builder")

    col1, col2 = st.columns(2)
    with col1:
    # STEP 1: Meal Name Selection
        meal_name = st.selectbox(
            "Meal Name",
            ["Breakfast", "Lunch", "Dinner", "Snack", "Post-Workout"],
            key="meal_name_select",
        )

    with col2:
        # STEP 2: Quick Add Selection
        quick_add_meals = define_quick_add_meals()
        food_item = st.selectbox(
            "Quick Add",
            list(quick_add_meals.keys()),
            key="quick_add_select",
            on_change=update_macro_inputs
        )

    st.divider()

    # STEP 3: Auto-fill and Allow Editing
    st.subheader("⚙️ Edit Macros")

    # Get preset values from quick add
    preset = quick_add_meals[food_item]

    col_cal, col_pro, col_carb = st.columns(3)

    with col_cal:
        calories = st.number_input(
            "Calories",
            min_value=0,
            step=1,
            value=int(preset["calories"]),
            key="cal_input",
        )

    with col_pro:
        protein = st.number_input(
            "Protein (g)",
            min_value=0.0,
            step=1.0,
            value=float(preset["protein"]),
            key="pro_input",
        )

    with col_carb:
        carbs = st.number_input(
            "Carbs (g)",
            min_value=0.0,
            step=1.0,
            value=float(preset["carbs"]),
            key="carb_input",
        )

    col_fat, col_water = st.columns(2)

    with col_fat:
        fats = st.number_input(
            "Fats (g)",
            min_value=0.0,
            step=1.0,
            value=float(preset["fats"]),
            key="fat_input",
        )

    with col_water:
        water = st.number_input(
            "Water (L)",
            min_value=0.0,
            step=0.1,
            value=float(preset["water"]),
            key="water_input",
        )

    st.divider()

    # STEP 4: Add Meal to Cart Button
    if st.button("➕ Add Meal to Cart", type="primary", use_container_width=True):
        # Validate that at least one macro has a value
        if calories == 0 and protein == 0 and carbs == 0 and fats == 0 and water == 0:
            st.error("Please enter at least one macro value.")
        else:
            # Append to pending meals
            st.session_state.pending_meals.append({
                "meal_name": meal_name,
                "food_item": food_item,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fats": fats,
                "water": water,
            })

            st.success(f"✓ Added {food_item} to cart!")
            st.rerun()

# ========================================================================
# PENDING MEALS DISPLAY (Below main area)
# ========================================================================

st.divider()
st.subheader("🛒 Pending Meals")

if st.session_state.pending_meals:
    # Display pending meals as expandable cards
    for idx, meal in enumerate(st.session_state.pending_meals):
        with st.expander(
            f"✓ {meal['meal_name']}: {meal['food_item']} - {meal['calories']} cal"
        ):
            # Show meal details
            cols = st.columns(5)
            cols[0].metric("Calories", f"{meal['calories']}")
            cols[1].metric("Protein", f"{meal['protein']:.0f}g")
            cols[2].metric("Carbs", f"{meal['carbs']:.0f}g")
            cols[3].metric("Fats", f"{meal['fats']:.0f}g")
            cols[4].metric("Water", f"{meal['water']:.1f}L")

            if st.button(
                "🗑️ Remove from Cart",
                key=f"remove_meal_{idx}",
                use_container_width=True,
            ):
                st.session_state.pending_meals.pop(idx)
                st.rerun()

    st.divider()

    # Pending totals summary
    st.subheader("📈 Pending Totals")
    pending_totals = calculate_pending_totals()

    cols = st.columns(5)
    cols[0].metric("Calories", f"{pending_totals['calories']}")
    cols[1].metric("Protein", f"{pending_totals['protein']:.0f}g")
    cols[2].metric("Carbs", f"{pending_totals['carbs']:.0f}g")
    cols[3].metric("Fats", f"{pending_totals['fats']:.0f}g")
    cols[4].metric("Water", f"{pending_totals['water']:.1f}L")

    st.divider()

    # Finish Day button (UPSERT logic)
    if st.button(
        "✓ Finish Day (Commit to Database)",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Saving meals..."):
            try:
                # Get or create today's nutrition log
                today_nutrition = get_todays_nutrition()
                log_id = today_nutrition["log_id"] if today_nutrition else None

                # Calculate delta macros from pending meals
                pending_totals = calculate_pending_totals()

                # UPSERT nutrition_logs (INSERT or UPDATE)
                log_id = upsert_nutrition_logs(log_id, pending_totals)

                if log_id:
                    # Insert meal entries
                    if insert_meal_entries(log_id):
                        st.success(
                            f"🎉 Day committed! {len(st.session_state.pending_meals)} meals saved."
                        )
                        st.session_state.pending_meals = []
                        st.rerun()
                    else:
                        st.error("Failed to save meal entries.")
                else:
                    st.error("Failed to create/update daily nutrition log.")

            except Exception as e:
                st.error(f"Error: {e}")

else:
    st.caption("_No meals added yet. Select a meal and add it to your cart._")
