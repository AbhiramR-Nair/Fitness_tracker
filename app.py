"""
Protocol Telemetry - Fitness Tracking Dashboard
Home page for the multipage application.
"""

import streamlit as st

st.set_page_config(page_title="Protocol Telemetry", layout="centered")
st.title("Protocol Telemetry")
st.subheader("Personalized Performance & Recovery Dashboard")

st.markdown("""
Welcome to your comprehensive fitness telemetry system. Track your training, nutrition, body composition, and recovery metrics all in one place.

### Navigation

Use the sidebar to explore the following sections:

- **Gym**: Log mechanical tension workouts (splits: Push, Pull, Legs, Core/Abs, Forearms/Grip)
- **Swim**: Track cardiovascular capacity and swimming sessions
- **Nutrition**: Record biochemical inputs (calories, macros, water)
- **Body**: Monitor anthropometric data and body composition
- **Recovery**: Log systemic fatigue metrics (sleep, RHR, pain scales)
- **Dashboard**: View comprehensive telemetry analytics and forecasts

### Getting Started

1. Navigate to each section to log your daily data
2. Use the Dashboard to review trends, consistency, and predictive forecasts
3. All data is synchronized to your Supabase backend in real-time

### Key Metrics Tracked

| Category | Metrics |
|----------|---------|
| **Training** | Tonnage, 1RM estimates, split balance, workout frequency |
| **Cardiovascular** | Swim pace, lap times, work capacity |
| **Nutrition** | Calories, protein, carbs, fats, water intake |
| **Anthropometry** | Weight, waist, shoulders, chest, arms, legs |
| **Recovery** | Sleep duration, RHR, pain discomfort scales |

---
*Data synced daily | All measurements stored securely in PostgreSQL*
""")