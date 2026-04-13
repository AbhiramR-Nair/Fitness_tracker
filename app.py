import streamlit as st
import pandas as pd
import numpy as np
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



# Create the 6 Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Gym", "Swim", "Nutrition", "Body", "Recovery", "Dashboard"])

# Tab 1: Mechanical Tension
with tab1:
    st.header("Mechanical Tension")
    
    # 1. Add the Rest Day Toggle at the top
    is_rest_day = st.checkbox("Today is a Rest Day")
    
    if is_rest_day:
        st.toast("Enjoy the recovery. Muscular repair happens today.")
        
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
                st.toast("Rest day logged successfully.")
            else:
                st.error("Failed to log rest day.")
                
    else:
        # Treat Core and Forearms as standard splits to unify the logic
        workout_type = st.selectbox("Split", ["Push", "Pull", "Legs", "Core/Abs", "Forearms/Grip"])

        # Clean dynamic filtering based on the split
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
        elif workout_type == "Legs":        
            exercise = st.selectbox("Movement", ["Leg Press", "Bulgarian Split Squats",
                                                "Leg Extensions", "Leg Curls",
                                                "Smith Machine Squats", "Abductor Machine", 
                                                "Adductor Machine", "Calf Raises",
                                                "Sumo squats", "Hip Thrusts"])
        elif workout_type == "Core/Abs":
            exercise = st.selectbox("Movement", ["Ab Crunches", "Hanging Leg Raises", 
                                                "Ab crunch machine", "Sit-ups", "Russian Twists", "Heel Touches"])
        elif workout_type == "Forearms/Grip":
            exercise = st.selectbox("Movement", ["Wrist Curls", "Reverse Wrist Curls", 
                                                "Natural Forearm Curls", "Natural Reverse Forearm Curls"])

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
            
        if st.button("Log Gym Session"):
            today = str(datetime.now().date())
            
            # --- HELPER FUNCTION FOR NORMALIZED INSERTS ---
            def insert_exercise_data(ex_name, split_type, num_sets, weight_val, rep_val, rir_val=None):
                parent_data = {"date": today, "workout_type": split_type, "exercise": ex_name}
                parent_resp = supabase.table("gym_logs").insert(parent_data).execute()
                
                if parent_resp.data:
                    new_id = parent_resp.data[0]['log_id']
                    
                    child_data = []
                    for i in range(num_sets):
                        child_data.append({
                            "log_id": new_id,
                            "set_number": i + 1,
                            "weight": weight_val if not isinstance(weight_val, list) else weight_val[i],
                            "reps": rep_val if not isinstance(rep_val, list) else rep_val[i],
                            "rir": rir_val if not isinstance(rir_val, list) else (rir_val[i] if rir_val else None)
                        })
                    if child_data:
                        supabase.table("exercise_sets").insert(child_data).execute()
                    return True
                return False

            # --- SINGLE UNIFIED ROUTE ---
            main_weights = [st.session_state[f"weight_{i}"] for i in range(sets)]
            main_reps = [st.session_state[f"reps_{i}"] for i in range(sets)]
            main_rirs = [st.session_state[f"rir_{i}"] for i in range(sets)]
            
            if insert_exercise_data(exercise, workout_type, sets, main_weights, main_reps, main_rirs):
                st.toast(f"Successfully logged {sets} sets of {exercise}.")
            else:
                st.error("Failed to log the session.")
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
                st.toast("Swim rest day logged successfully.")
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
        
        total_laps = length / 50 
        avg_lap_time = duration / total_laps if total_laps > 0 else 0
    
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
                st.toast("Swim data appended via API.")
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
            st.toast("Nutrition data appended via API.")
        else:
            st.error("Failed to append data.")


# Tab 4: Body Data
with tab4:
    st.header("Anthropometric Data")
    daily_weight = st.number_input("Morning Weight (kg)", step=0.05)
    
    # Initialize optional variables to prevent scope leaks
    waist = shoulders = chest = arms = legs = None
    
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

        
        data = {
            "date": today, 
            "daily_weight": daily_weight,
            "waist": waist, 
            "shoulders": shoulders, 
            "chest": chest,
            "arms": arms, 
            "legs": legs
        }
        
        response = supabase.table("body_metrics").insert(data).execute()
        
        if response.data:
            st.toast("Body data appended via API.")
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
            st.toast("Recovery data appended via API.")
        else:
            st.error("Failed to append data.")
 
# Tab 6: Telemetry Dashboard       
with tab6:
    st.header("Telemetry Dashboard")
    
    if st.button("Refresh Data", type="primary"):
        
        # --- 1. EXTRACT & TRANSFORM ---
        body_resp = supabase.table("body_metrics").select("date, daily_weight").order("date").execute()
        rec_resp = supabase.table("recovery_logs").select("date, sleep_hrs, rhr, shoulder_pain").order("date").execute()
        nut_resp = supabase.table("nutrition_logs").select("date, calories, protein, carbs, fats, water_l").order("date").execute()
        gym_resp = supabase.table("gym_logs").select("log_id, date, workout_type, exercise").execute()
        sets_resp = supabase.table("exercise_sets").select("log_id, weight, reps").execute()
        swim_resp = supabase.table("swim_logs").select("date, avg_lap_time, length_m").order("date").execute()

        body_df = pd.DataFrame(body_resp.data)
        rec_df = pd.DataFrame(rec_resp.data)
        nut_df = pd.DataFrame(nut_resp.data)
        gym_df = pd.DataFrame(gym_resp.data)
        sets_df = pd.DataFrame(sets_resp.data)
        swim_df = pd.DataFrame(swim_resp.data)

        # Typecasting JSON to numeric
        if not body_df.empty: body_df['daily_weight'] = pd.to_numeric(body_df['daily_weight'], errors='coerce')
        if not nut_df.empty: nut_df[['calories', 'protein', 'carbs', 'fats', 'water_l']] = nut_df[['calories', 'protein', 'carbs', 'fats', 'water_l']].apply(pd.to_numeric, errors='coerce')
        if not rec_df.empty: rec_df[['sleep_hrs', 'rhr', 'shoulder_pain']] = rec_df[['sleep_hrs', 'rhr', 'shoulder_pain']].apply(pd.to_numeric, errors='coerce')

        # Complex Gym Transformations (Tonnage & 1RM)
        if not gym_df.empty and not sets_df.empty:
            merged_gym = pd.merge(sets_df, gym_df, on="log_id")
            merged_gym['tonnage'] = merged_gym['weight'] * merged_gym['reps']
            # Brzycki 1RM Formula: Weight × (36 / (37 - Reps))
            merged_gym['est_1rm'] = merged_gym.apply(lambda row: row['weight'] if row['reps'] == 1 else row['weight'] * (36 / (37 - row['reps'])), axis=1)
        else:
            merged_gym = pd.DataFrame()

        # --- 2. KPI ROW ---
        st.subheader("Peak Mechanical Outputs (Est. 1RM)")
        col1, col2, col3, col4 = st.columns(4)
        
        def get_max_1rm(ex_name):
            if not merged_gym.empty and ex_name in merged_gym['exercise'].values:
                return round(merged_gym[merged_gym['exercise'] == ex_name]['est_1rm'].max(), 1)
            return "--"

        col1.metric("Squat 1RM", f"{get_max_1rm('Smith Machine Squats')} kg")
        col2.metric("Bench 1RM", f"{get_max_1rm('Bench Press')} kg")
        col3.metric("Deadlift 1RM", f"{get_max_1rm('Deadlift')} kg")
        
        if not swim_df.empty and swim_df['avg_lap_time'].min() > 0:
            fastest_lap = round(swim_df[swim_df['avg_lap_time'] > 0]['avg_lap_time'].min(), 2)
            col4.metric("Best Lap", f"{fastest_lap} min")
        else:
            col4.metric("Best Lap", "-- min")
                
        st.divider()
        
        
        #GITHUB STYLE HEATMAP FOR ACTIVITY CONSISTENCY (GYM + SWIM)
        st.subheader("Activity Consistency Heatmap")
        
        # 1. Extract unique dates from the dataframes
        gym_dates = pd.to_datetime(gym_df['date']).dt.date.unique() if not gym_df.empty else []
        swim_dates = pd.to_datetime(swim_df['date']).dt.date.unique() if not swim_df.empty else []
            
        # 2. Generate a continuous timeline for the last 180 days (fits dashboards well)
        end_date = datetime.now().date()
        start_date = end_date - pd.Timedelta(days=180)
        all_dates = pd.date_range(start=start_date, end=end_date)
            
        heat_df = pd.DataFrame({'date': all_dates})
            
        # 3. Categorize each day
        heat_df['is_gym'] = heat_df['date'].dt.date.isin(gym_dates)
        heat_df['is_swim'] = heat_df['date'].dt.date.isin(swim_dates)
            
        def get_activity_status(row):
            if row['is_gym'] and row['is_swim']: return 3  # Gym + Swim
            if row['is_swim']: return 2                    # Swim Only
            if row['is_gym']: return 1                     # Gym Only
            return 0                                       # Rest Day
                
        heat_df['status'] = heat_df.apply(get_activity_status, axis=1)
            
        # 4. Math for GitHub-style layout (Y = Day of Week, X = Week offset)
        heat_df['dow'] = heat_df['date'].dt.dayofweek
        heat_df['week'] = ((heat_df['date'] - pd.to_datetime(start_date)).dt.days) // 7
            
        # Pivot into a 2D matrix
        matrix = heat_df.pivot(index='dow', columns='week', values='status')
            
        # Create hover text matrix
        hover_text = []
        status_map = {0: "Rest", 1: "Gym", 2: "Swim", 3: "Gym + Swim"}
        for dow in range(7):
            row_text = []
            for week in matrix.columns:
                val = heat_df[(heat_df['dow'] == dow) & (heat_df['week'] == week)]
                if not val.empty:
                    d = val.iloc[0]
                    row_text.append(f"{d['date'].strftime('%b %d, %Y')}<br>{status_map[d['status']]}")
                else:
                    row_text.append("")
            hover_text.append(row_text)

            # 5. Build the discrete color scale
        colorscale = [
            [0.00, '#1e212b'], [0.25, '#1e212b'], # 0: Rest (Dark)
            [0.25, '#ff4b4b'], [0.50, '#ff4b4b'], # 1: Gym (Red)
            [0.50, '#00ffcc'], [0.75, '#00ffcc'], # 2: Swim (Cyan)
            [0.75, '#b042ff'], [1.00, '#b042ff']  # 3: Gym+Swim (Purple)
            ]
            
            # 6. Render the Heatmap
        fig_heat = go.Figure(data=go.Heatmap(
            z=matrix.values,
            text=hover_text,
            hoverinfo="text",
            colorscale=colorscale,
            showscale=False,
            xgap=2, ygap=2, # Creates the "blocky" gap between days
            zmin=0, zmax=0
            ))
            
        fig_heat.update_layout(
            yaxis=dict(
                tickmode='array',
                tickvals=[0, 1, 2, 3, 4, 5, 6],
                ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                autorange="reversed", # Puts Monday at the top
                scaleanchor="x", # Ensures square cells
                scaleratio=1
            ),
            xaxis=dict(showticklabels=False), # Hide week numbers
            margin=dict(l=20, r=20, t=30, b=20),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
            
        st.plotly_chart(fig_heat, use_container_width=True)
            
        # Render a manual legend below it
        st.markdown(
        """
        <div style='display: flex; justify-content: center; gap: 15px; font-size: 12px; margin-top: -10px;'>
        <div><span style='color: #1e212b;'>█</span> Rest</div>
        <div><span style='color: #ff4b4b;'>█</span> Gym</div>
        <div><span style='color: #00ffcc;'>█</span> Swim</div>
        <div><span style='color: #b042ff;'>█</span> Gym + Swim</div>
        </div>
        """, unsafe_allow_html=True
        )    
        
        st.divider()

        # --- 3. CONSISTENCY HEATMAP & RADAR ---
        col_heat, col_radar = st.columns([2, 1])
        
        with col_heat:
            st.subheader("Training Consistency")
            if not merged_gym.empty:
                daily_tonnage = merged_gym.groupby('date')['tonnage'].sum().reset_index()
                # A density bar chart that functions as a Github-style activity heat-strip
                fig_heat = px.bar(daily_tonnage, x="date", y="tonnage", color="tonnage",
                                  color_continuous_scale="Tealgrn", title="Daily Work Capacity Streak")
                fig_heat.update_layout(xaxis_title="", yaxis_title="Total Volume (kg)")
                st.plotly_chart(fig_heat, use_container_width=True)
            else:
                st.info("Log workouts to build your streak.")
                
        with col_radar:
            st.subheader("Split Balance")
            if not merged_gym.empty:
                # Group by Split to see where total energy is going
                radar_data = merged_gym.groupby('workout_type')['tonnage'].sum().reset_index()
                fig_radar = go.Figure(data=go.Scatterpolar(
                    r=radar_data['tonnage'],
                    theta=radar_data['workout_type'],
                    fill='toself',
                    line_color='#00ffcc'
                ))
                fig_radar.update_layout(polar=dict(radialaxis=dict(visible=False)), showlegend=False, 
                                        margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_radar, use_container_width=True)

        st.divider()

        # --- 4. PREDICTIVE FORECASTING (OLS Regression) ---
        st.subheader("Body Recomposition Forecast")
        if not body_df.empty and len(body_df) > 2:
            body_df['date'] = pd.to_datetime(body_df['date'])
            body_df = body_df.sort_values('date')
            
            # Calculate rolling average
            body_df['7_Day_Avg'] = body_df['daily_weight'].rolling(window=7, min_periods=1).mean()
            
            # Linear Regression Math
            body_df['days_since_start'] = (body_df['date'] - body_df['date'].min()).dt.days
            z = np.polyfit(body_df['days_since_start'], body_df['daily_weight'], 1)
            p = np.poly1d(z)
            
            # Project 30 days into the future
            future_days = np.arange(body_df['days_since_start'].max(), body_df['days_since_start'].max() + 30)
            future_dates = pd.date_range(body_df['date'].max(), periods=30)
            future_weights = p(future_days)
            
            fig_weight = go.Figure()
            # Actual Data
            fig_weight.add_trace(go.Scatter(x=body_df['date'], y=body_df['daily_weight'], mode='lines', name='Daily Weight', line=dict(color='gray', width=1)))
            fig_weight.add_trace(go.Scatter(x=body_df['date'], y=body_df['7_Day_Avg'], mode='lines', name='7-Day Avg', line=dict(color='#00ffcc', width=3)))
            # Projection Line
            fig_weight.add_trace(go.Scatter(x=future_dates, y=future_weights, mode='lines', name='30-Day Forecast', line=dict(color='red', width=2, dash='dash')))
            
            fig_weight.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Goal: 80 kg")
            fig_weight.update_layout(title="Current Trajectory vs. 30-Day Predictive Forecast")
            st.plotly_chart(fig_weight, use_container_width=True)
        else:
            st.info("Log at least 3 days of body weight data to generate the predictive model.")

        st.divider()

        # --- 5. SYSTEMIC FATIGUE & METABOLISM (Preserved from earlier) ---
        st.subheader("Metabolic & Cardiovascular Telemetry")
        if not swim_df.empty and not rec_df.empty:
            swim_daily = swim_df.groupby('date').mean(numeric_only=True).reset_index()
            rec_daily = rec_df.groupby('date').mean(numeric_only=True).reset_index()
            cardio_df = pd.merge(swim_daily, rec_daily, on="date", how="inner")
            if not cardio_df.empty:
                fig_cardio = go.Figure()
                fig_cardio.add_trace(go.Scatter(x=cardio_df['date'], y=cardio_df['avg_lap_time'], mode='lines+markers', name='Swim Pace', line=dict(color='cyan')))
                fig_cardio.add_trace(go.Scatter(x=cardio_df['date'], y=cardio_df['rhr'], mode='lines+markers', name='RHR', line=dict(color='red'), yaxis='y2'))
                fig_cardio.update_layout(title="Cardiovascular Engine (Pace vs. RHR)",
                    yaxis=dict(title=dict(text="Pace (min/lap)", font=dict(color="cyan")), tickfont=dict(color="cyan")),
                    yaxis2=dict(title=dict(text="RHR (bpm)", font=dict(color="red")), tickfont=dict(color="red"), overlaying='y', side='right'))
                st.plotly_chart(fig_cardio, use_container_width=True)

        if not nut_df.empty:
            nut_df['Cal_7_Day_Avg'] = nut_df['calories'].rolling(window=7, min_periods=1).mean()
            fig_cal = px.line(nut_df, x="date", y=["calories", "Cal_7_Day_Avg"], title="Metabolic Intake", color_discrete_sequence=['gray', '#00ffcc'])
            fig_cal.add_hline(y=3000, line_dash="dash", line_color="orange", annotation_text="Surplus Target")
            st.plotly_chart(fig_cal, use_container_width=True)