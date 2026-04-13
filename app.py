import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

st.set_page_config(page_title="Sleeper Build Tracker", layout="centered")
st.title("Protocol Telemetry")

# Initialize the REST API client for Supabase
@st.cache_resource
def init_connection():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_connection() 



# Create the 5 Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Gym", "Swim", "Nutrition", "Body", "Recovery", "Dashboard"])

# Tab 1: Mechanical Tension
with tab1:
    st.header("Mechanical Tension")
    
    # 1. Add the Rest Day Toggle at the top
    is_rest_day = st.checkbox("Today is a Rest Day")
    
    if is_rest_day:
        st.success("Enjoy the recovery. Muscular repair happens today.")
        
        if st.button("Log Gym Rest Day"):
            today = str(datetime.now().date())
            
            # Send a specific "Rest" record to the parent table
            parent_data = {
                "date": today, 
                "workout_type": "Rest", 
                "exercise": "None",
            }
            
            response = supabase.table("gym_logs").insert(parent_data).execute()
            if response.data:
                st.success("Rest day logged successfully.")
            else:
                st.error("Failed to log rest day.")
                
    else:
        # 2. Indent your normal workout logic here
        workout_type = st.selectbox("Split", ["Push", "Pull", "Legs"])
        
        # ... [Keep all your existing exercise logic, Abs, Forearms, and the "Log Gym Session" button exactly as they are here] ...
        # Dynamic Filtering
        if workout_type == "Push":
            exercise = st.selectbox("Movement", ["Bench Press", "Incline DB Press", 
                                                "Peck Deck Flyes", "Incline DB Flyes", 
                                                "Lateral Raises", "Front Raises", 
                                                "Shoulder Press", "Shoulder Shrug",
                                                "Cable lateral raises", "Overhead Tricep Extensions", 
                                                "Rope Tricep Extensions", "Single arm tricep Extensions",
                                                "Reverse tricep extensions"])
        elif workout_type == "Pull":
            exercise = st.selectbox("Movement", ["Deadlift", "Close Grip Lat Pulldown", 
                                                "Wide Grip Lat Pulldown", "Seated Row", 
                                                "Wide Grip Seated Row", "Hyperextensions",
                                                "Cable Face Pulls", "Reverse Pec Deck Flyes",
                                                "EZ Bar Curls", "Dumbbell Curls", "Hammer Curls",
                                                "Preacher Curls"])
        else:        
            exercise = st.selectbox("Movement", ["Leg Press", "Bulgarian Split Squats",
                                                "Leg Extensions", "Leg Curls",
                                                "Smith Machine Squats", "Abductor Machine", 
                                                "Adductor Machine", "Calf Raises",
                                                "Sumo squats", "Hip Thrusts"])
    
        st.subheader("Session Details")
        sets = st.number_input("Set Number", min_value=1, step=1)
        for i in range(sets):
            col1, col2, col3 = st.columns(3)
            with col1:
                weight = st.number_input("Weight (kg)", step=0.5, key=f"weight_{i}")
            with col2:
                reps = st.number_input("Reps", min_value=8, max_value=20, step=1, key=f"reps_{i}")
            with col3:
                rir = st.number_input("RIR", min_value=0, max_value=5, key=f"rir_{i}")
            
        if st.checkbox("Abs and Core Work"):
            abs_exercise = st.selectbox("Abs Exercise", ["Cable Crunches", "Hanging Leg Raises", 
                                                        "Ab crunch machine", "Sit-ups", "Russian Twists"])
            col1, col2, col3 = st.columns(3)
            with col1:
                abs_weight = st.number_input("Abs Weight (kg)", step=0.5)
            with col2:
                abs_sets = st.number_input("Abs Sets", min_value=1, step=1)
            with col3:
                abs_reps = st.number_input("Abs Reps", min_value=10, step=1)
            
        if st.checkbox("Forearm Work"):
            forearm_exercise = st.selectbox("Forearm Exercise", ["Wrist Curls", "Reverse Wrist Curls", 
                                                                "Natural Forearm Curls", "Natural Reverse Forearm Curls"])
            col1, col2, col3 = st.columns(3)
            with col1:
                forearm_weight = st.number_input("Forearm Weight (kg)", step=0.5)
            with col2:
                forearm_sets = st.number_input("Forearm Sets", min_value=1, step=1)
            with col3:
                forearm_reps = st.number_input("Forearm Reps", min_value=10, step=1)
            
        if st.button("Log Gym Session"):
            # SQL Insert Command Here
            today = str(datetime.now().date())
            
            # Safely capture optional Abs and Forearm data
            a_ex = abs_exercise if 'abs_exercise' in locals() else None
            a_w = abs_weight if 'abs_weight' in locals() else None
            a_s = abs_sets if 'abs_sets' in locals() else None
            a_r = abs_reps if 'abs_reps' in locals() else None
            
            f_ex = forearm_exercise if 'forearm_exercise' in locals() else None
            f_w = forearm_weight if 'forearm_weight' in locals() else None
            f_s = forearm_sets if 'forearm_sets' in locals() else None
            f_r = forearm_reps if 'forearm_reps' in locals() else None
            
            # STEP 1: Insert Parent Record
            parent_data = {
                "date": today, "workout_type": workout_type, "exercise": exercise,
                "abs_exercise": a_ex, "abs_weight": a_w, "abs_sets": a_s, "abs_reps": a_r,
                "forearm_exercise": f_ex, "forearm_weight": f_w, "forearm_sets": f_s, "forearm_reps": f_r
            }
            
            parent_response = supabase.table("gym_logs").insert(parent_data).execute()
            
            if parent_response.data:
                # Fetch the generated UUID from the response
                new_log_id = parent_response.data[0]['log_id']
                
                # STEP 2: Package all sets into a list and insert into Child table
                child_data = []
                for i in range(sets):
                    child_data.append({
                        "log_id": new_log_id,
                        "set_number": i + 1,
                        "weight": st.session_state[f"weight_{i}"],
                        "reps": st.session_state[f"reps_{i}"],
                        "rir": st.session_state[f"rir_{i}"]
                    })
                
                if child_data:
                    supabase.table("exercise_sets").insert(child_data).execute()
                    
                st.success(f"Successfully logged {exercise} and {sets} sets via API.")
            else:
                st.error("Failed to log the main exercise.")

# Tab 2: Swimming
with tab2:
    st.header("Cardiovascular Capacity")
    # 1. Add the Rest Day Toggle
    is_swim_rest = st.checkbox("No Swimming Today")
    
    if is_swim_rest:
        st.info("Central nervous system recovery logged.")
        
        if st.button("Log Swim Rest Day"):
            today = str(datetime.now().date())
            
            # Log the explicit rest
            data = {
                "date": today, 
                "swim_type": "Rest", 
                "duration_min": 0, 
                "length_m": 0, 
                "avg_lap_time": 0.0
            }
            
            response = supabase.table("swim_logs").insert(data).execute()
            if response.data:
                st.success("Swim rest day logged successfully.")
            else:
                st.error("Failed to log rest day.")
                
    else:
        # 2. Indent your normal swim logic here
        swim_type = st.selectbox("Swim Type", ["Endurance", "Sprints"])
        
        col1, col2 = st.columns(2)
        with col1: 
            duration = st.number_input("Duration (minutes)", step=5, min_value=5)
        with col2:
            length = st.number_input("Length (meters)", step=50, min_value=50)    
        
        avg_lap_time = length / duration
    
        if st.button("Log Swim Session"): 
            # SQL Insert Command Here
            today = str(datetime.now().date())
            
            data = {
                "date": today, 
                "swim_type": swim_type, 
                "duration_min": duration, 
                "length_m": length, 
                "avg_lap_time": avg_lap_time
            }
            
            response = supabase.table("swim_logs").insert(data).execute()
            
            if response.data:
                st.success("Swim data appended via API.")
            else:
                st.error("Failed to append data.")
        

# Tab 3: Nutrition
with tab3:
    st.header("Biochemical Inputs")
    # Number inputs for Calories, Protein, Carbs, Fats, Water.
    col1, col2 = st.columns(2)
    with col1:
        calories = st.number_input("Calories", step=1)
        protein = st.number_input("Protein (g)", step=1)
        carbs = st.number_input("Carbs (g)", step=1)
    with col2:    
        fats = st.number_input("Fats (g)", step=1)
        water = st.number_input("Water (L)", step=1)
        
    if st.button("Log Nutrition"):
        # SQL Insert Command Here
        today = str(datetime.now().date())
        
# Create a Python dictionary of your data
        data = {
            "date": today, 
            "calories": calories, 
            "protein": protein, 
            "carbs": carbs, 
            "fats": fats, 
            "water_l": water
        }
        
        # Send it to the cloud via HTTPS
        response = supabase.table("nutrition_logs").insert(data).execute()
        
        if response.data:
            st.success("Nutrition data appended via API.")
        else:
            st.error("Failed to append data.")


# Tab 4: Body Data
with tab4:
    st.header("Anthropometric Data")
    daily_weight = st.number_input("Morning Weight (kg)", step=0.05)
    
    # Hidden Weekly Measurements
    if st.checkbox("Log Bi-Weekly Tape Measurements"):
        col1, col2 = st.columns(2)
        with col1:
            waist = st.number_input("Waist (cm)")
            shoulders = st.number_input("Shoulders (cm)")
            chest = st.number_input("Chest (cm)")
        with col2:
            arms = st.number_input("Arms (cm)")
            legs = st.number_input("Legs (cm)")

    if st.button("Log Body Data"):
        # SQL Insert Command Here
        today = str(datetime.now().date())
        
        # Safely capture optional tape measurements
        wst = waist if 'waist' in locals() else None
        shld = shoulders if 'shoulders' in locals() else None
        chst = chest if 'chest' in locals() else None
        arm = arms if 'arms' in locals() else None
        leg = legs if 'legs' in locals() else None
        
        data = {
            "date": today, 
            "daily_weight": daily_weight,
            "waist": wst, 
            "shoulders": shld, 
            "chest": chst,
            "arms": arm, 
            "legs": leg
        }
        
        response = supabase.table("body_metrics").insert(data).execute()
        
        if response.data:
            st.success("Body data appended via API.")
        else:
            st.error("Failed to append data.")
        
        
# Tab 5: Systemic Fatigue and Recovery        
with tab5:
    st.header("Systemic Fatigue")
    st.subheader("Recovery Metrics")
    col1, col2 = st.columns(2)
    with col1:
        sleep_hrs = st.number_input("Sleep Duration (hrs)", step=0.5)
    with col2:
        rhr = st.number_input("Resting Heart Rate", step=1)
    st.subheader("Discomfort Scales")
    col1, col2 = st.columns(2)    
    with col1:
        shoulder_pain = st.slider("Shoulder Discomfort Scale", 0, 10, 0)
        elbow_pain = st.slider("Elbow Discomfort Scale", 0, 10, 0)
    with col2:
        wrist_pain = st.slider("Wrist Discomfort Scale", 0, 10, 0)
        lower_back_pain = st.slider("Lower Back Discomfort Scale", 0, 10, 0)
    pain_note = st.text_area("Pain Notes")
    
    if st.button("Log Recovery Data"): 
        # SQL Insert Command Here
        today = str(datetime.now().date())
        
        data = {
            "date": today, 
            "sleep_hrs": sleep_hrs, 
            "rhr": rhr, 
            "shoulder_pain": shoulder_pain, 
            "elbow_pain": elbow_pain, 
            "wrist_pain": wrist_pain, 
            "lower_back_pain": lower_back_pain, 
            "pain_notes": pain_note
        }
        
        response = supabase.table("recovery_logs").insert(data).execute()
        
        if response.data:
            st.success("Recovery data appended via API.")
        else:
            st.error("Failed to append data.")
        
with tab6:
    st.header("Telemetry Dashboard")
    
    if st.button("Refresh Data"):
        
        # --- 1. EXTRACT: Pull all necessary tables via REST API ---
        body_resp = supabase.table("body_metrics").select("date, daily_weight").order("date").execute()
        rec_resp = supabase.table("recovery_logs").select("date, sleep_hrs, rhr, shoulder_pain").order("date").execute()
        nut_resp = supabase.table("nutrition_logs").select("date, calories, protein, carbs, fats, water_l").order("date").execute()
        gym_resp = supabase.table("gym_logs").select("log_id, date, workout_type, exercise").execute()
        sets_resp = supabase.table("exercise_sets").select("log_id, weight, reps").execute()
        swim_resp = supabase.table("swim_logs").select("date, avg_lap_time, length_m").order("date").execute()

        # Convert to Pandas DataFrames
        body_df = pd.DataFrame(body_resp.data)
        rec_df = pd.DataFrame(rec_resp.data)
        nut_df = pd.DataFrame(nut_resp.data)
        gym_df = pd.DataFrame(gym_resp.data)
        sets_df = pd.DataFrame(sets_resp.data)
        swim_df = pd.DataFrame(swim_resp.data)

        # --- 2. TRANSFORM: Merge relational tables and calculate metrics ---
        if not gym_df.empty and not sets_df.empty:
            merged_gym = pd.merge(sets_df, gym_df, on="log_id")
            # Calculate total tonnage per set
            merged_gym['tonnage'] = merged_gym['weight'] * merged_gym['reps']
        else:
            merged_gym = pd.DataFrame()

        # --- 3. KPI ROW: Personal Records ---
        st.subheader("Performance PRs")
        col1, col2 = st.columns(2)
        
        with col1:
            if not merged_gym.empty and 'Smith Machine Squats' in merged_gym['exercise'].values:
                smith_max = merged_gym[merged_gym['exercise'] == 'Smith Machine Squats']['weight'].max()
                st.metric("Smith Squat PR", f"{smith_max} kg")
            else:
                st.metric("Smith Squat PR", "-- kg")
                
            if not merged_gym.empty and 'Deadlift' in merged_gym['exercise'].values:
                deadlift_max = merged_gym[merged_gym['exercise'] == 'Deadlift']['weight'].max()
                st.metric("Deadlift PR", f"{deadlift_max} kg")
            else:
                st.metric("Deadlift PR", "-- kg")
                
        with col2:
            if not merged_gym.empty and 'Bench Press' in merged_gym['exercise'].values:
                bench_max = merged_gym[merged_gym['exercise'] == 'Bench Press']['weight'].max()
                st.metric("Bench Press PR", f"{bench_max} kg")
            else:
                st.metric("Bench Press PR", "-- kg")
                
            if not swim_df.empty and swim_df['length_m'].min() > 0:
                total_lap = round(swim_df[swim_df['length_m'] > 0]['length_m'].min(), 2)
                st.metric("Best Total Swim Length", f"{total_lap} mts")
            else:
                st.metric("Best Total Swim Length", "-- mts")
                
        st.divider()

        # --- 4. MECHANICAL VOLUME & SPLIT DISTRIBUTION ---
        col_vol, col_split = st.columns([2, 1])
        
        with col_vol:
            st.subheader("Daily Tonnage Trajectory")
            if not merged_gym.empty:
                daily_tonnage = merged_gym.groupby('date')['tonnage'].sum().reset_index()
                fig_tonnage = px.line(daily_tonnage, x="date", y="tonnage", markers=True,
                                      title="Total Mechanical Volume (Weight × Reps)",
                                      labels={"tonnage": "Total Volume (kg)", "date": "Date"})
                st.plotly_chart(fig_tonnage, use_container_width=True)
            else:
                st.info("Log gym sets to calculate tonnage.")
                
        with col_split:
            st.subheader("Split Distribution")
            if not gym_df.empty:
                split_counts = gym_df['workout_type'].value_counts().reset_index()
                split_counts.columns = ['Split', 'Count']
                fig_split = px.pie(split_counts, values='Count', names='Split', hole=0.4,
                                   title="Workout Frequency")
                st.plotly_chart(fig_split, use_container_width=True)

        st.divider()

        # --- 5. CARDIOVASCULAR ADAPTATION (Dual Axis) ---
        st.subheader("Swim Efficiency vs. Resting Heart Rate")
        if not swim_df.empty and not rec_df.empty:
            # Merge swim and recovery on date to compare them on the same days
            cardio_df = pd.merge(swim_df, rec_df, on="date", how="inner")
            if not cardio_df.empty:
                fig_cardio = go.Figure()
                # Left Y-Axis: Swim Pace
                fig_cardio.add_trace(go.Scatter(x=cardio_df['date'], y=cardio_df['avg_lap_time'],
                                                mode='lines+markers', name='Avg Lap Time (min)',
                                                line=dict(color='cyan')))
                # Right Y-Axis: RHR
                fig_cardio.add_trace(go.Scatter(x=cardio_df['date'], y=cardio_df['rhr'],
                                                mode='lines+markers', name='Resting Heart Rate (bpm)',
                                                line=dict(color='red'), yaxis='y2'))
                
                fig_cardio.update_layout(
                    title="Cardiovascular Engine Adaptation",
                    yaxis=dict(
                        title=dict(text="Swim Pace (min/lap)", font=dict(color="cyan")), 
                        tickfont=dict(color="cyan")
                    ),
                    yaxis2=dict(
                        title=dict(text="RHR (bpm)", font=dict(color="red")), 
                        tickfont=dict(color="red"),
                        overlaying='y', 
                        side='right'
                    )
                )
                st.plotly_chart(fig_cardio, use_container_width=True)
            else:
                st.info("Log both swimming and recovery data on the same dates to see correlation.")
        else:
            st.info("Log swim and recovery data to build cardiovascular charts.")

        st.divider()

        # --- 6. ADVANCED CORRELATION MATRIX ---
        st.subheader("Systemic Fatigue Correlation Matrix")
        st.caption("A Pearson Correlation heatmap identifying relationships between volume, sleep, and discomfort.")
        if not merged_gym.empty and not rec_df.empty:
            daily_tonnage = merged_gym.groupby('date')['tonnage'].sum().reset_index()
            # Merge recovery and tonnage
            matrix_df = pd.merge(rec_df, daily_tonnage, on="date", how="inner")
            if not matrix_df.empty and len(matrix_df) > 2:
                # Select only numerical columns for the matrix
                corr_cols = ['sleep_hrs', 'rhr', 'shoulder_pain', 'tonnage']
                corr_matrix = matrix_df[corr_cols].corr().round(2)
                
                fig_corr = px.imshow(corr_matrix, text_auto=True, aspect="auto", 
                                     color_continuous_scale="RdBu_r", 
                                     title="Variable Impact Heatmap")
                st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("Need at least 3 days of overlapping gym and recovery data to compute statistical correlation.")
        else:
            st.info("Log both recovery and gym data to generate the heatmap.")

        st.divider()

        # --- 7. BODY RECOMPOSITION (Existing) ---
        st.subheader("Body Recomposition Trend")
        if not body_df.empty:
            body_df['7_Day_Avg'] = body_df['daily_weight'].rolling(window=7, min_periods=1).mean()
            fig_weight = px.line(body_df, x="date", y=["daily_weight", "7_Day_Avg"], 
                                 title="Daily Weight vs. 7-Day Average")
            fig_weight.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Goal: 80 kg")
            st.plotly_chart(fig_weight, use_container_width=True)
        else:
            st.info("Log more body weight data to generate the trend line.")

        st.divider()

        # --- 8. RECOVERY VS SLEEP (Existing) ---
        st.subheader("Shoulder Discomfort vs. Sleep")
        if not rec_df.empty:
            fig_recovery = px.bar(rec_df, x="date", y="sleep_hrs", 
                                  color="shoulder_pain", 
                                  color_continuous_scale="Reds",
                                  title="Sleep Duration Colored by Shoulder Pain Intensity")
            st.plotly_chart(fig_recovery, use_container_width=True)

        st.divider()

        # --- 9. METABOLIC INPUTS (Existing) ---
        st.subheader("Metabolic Inputs & Macronutrients")
        if not nut_df.empty:
            nut_df['Cal_7_Day_Avg'] = nut_df['calories'].rolling(window=7, min_periods=1).mean()
            fig_cal = px.line(nut_df, x="date", y=["calories", "Cal_7_Day_Avg"], 
                              title="Daily Caloric Intake vs. 7-Day Average",
                              labels={"value": "Calories", "variable": "Metric"})
            fig_cal.add_hline(y=3000, line_dash="dash", line_color="orange", annotation_text="Goal: 3000 kcal")
            fig_cal.add_hline(y=3500, line_dash="dash", line_color="red", annotation_text="Maintenance: 3500 kcal")
            st.plotly_chart(fig_cal, use_container_width=True)
            
            st.divider()
            
            fig_macros = px.line(nut_df, x="date", y=["protein", "carbs", "fats", "water_l"],
                                 title="Daily Macronutrient (g) & Water (L) Trajectory",
                                 labels={"value": "Amount", "variable": "Nutrient"})
            st.plotly_chart(fig_macros, use_container_width=True)
        else:
            st.info("Log more nutrition data to generate the dietary trends.")