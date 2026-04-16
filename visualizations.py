"""
Visualization module for complex Plotly diagrams and charts (Refactored).
All functions are pure Python (no Streamlit dependencies) and return Plotly Figure objects.
Updated to work with new UUID-based schemas.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta


def create_consistency_heatmap(gym_df: pd.DataFrame, swim_df: pd.DataFrame, days: int = 180) -> go.Figure:
    """
    Create a GitHub-style activity consistency heatmap.
    
    Args:
        gym_df: DataFrame with gym_logs data (must have 'date' column).
        swim_df: DataFrame with swim_logs data (must have 'date' column).
        days: Number of days to display (default 180).
    
    Returns:
        go.Figure: Plotly heatmap figure.
    """
    
    # Filter out explicitly logged Rest days before extracting dates
    if not gym_df.empty and "workout_type" in gym_df.columns:
        active_gym = gym_df[gym_df["workout_type"] != "Rest"]
    else:
        active_gym = gym_df
        
    if not swim_df.empty and "swim_type" in swim_df.columns:
        active_swim = swim_df[swim_df["swim_type"] != "Rest"]
    else:
        active_swim = swim_df

    # Extract unique dates from the active (non-rest) data
    gym_dates = pd.to_datetime(active_gym["date"]).dt.date.unique() if not active_gym.empty else []
    swim_dates = pd.to_datetime(active_swim["date"]).dt.date.unique() if not active_swim.empty else []
    
    # Generate continuous timeline
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    all_dates = pd.date_range(start=start_date, end=end_date)
    
    heat_df = pd.DataFrame({"date": all_dates})
    
    # Categorize each day
    heat_df["is_gym"] = heat_df["date"].dt.date.isin(gym_dates)
    heat_df["is_swim"] = heat_df["date"].dt.date.isin(swim_dates)
    
    def get_activity_status(row):
        if row["is_gym"] and row["is_swim"]:
            return 3  # Gym + Swim
        if row["is_swim"]:
            return 2  # Swim Only
        if row["is_gym"]:
            return 1  # Gym Only
        return 0  # Rest Day
    
    heat_df["status"] = heat_df.apply(get_activity_status, axis=1)
    
    # GitHub-style layout (Y = Day of Week, X = Week offset)
    heat_df["dow"] = heat_df["date"].dt.dayofweek
    heat_df["week"] = ((heat_df["date"] - pd.to_datetime(start_date)).dt.days) // 7
    
    # Pivot into 2D matrix
    matrix = heat_df.pivot(index="dow", columns="week", values="status")
    
    # Create hover text matrix
    hover_text = []
    status_map = {0: "Rest", 1: "Gym", 2: "Swim", 3: "Gym + Swim"}
    for dow in range(7):
        row_text = []
        for week in matrix.columns:
            val = heat_df[(heat_df["dow"] == dow) & (heat_df["week"] == week)]
            if not val.empty:
                d = val.iloc[0]
                row_text.append(f"{d['date'].strftime('%b %d, %Y')}<br>{status_map[d['status']]}")
            else:
                row_text.append("")
        hover_text.append(row_text)
    
    # Discrete color scale
    colorscale = [
        [0.00, "#1e212b"],
        [0.25, "#1e212b"],  # 0: Rest (Dark)
        [0.25, "#ff4b4b"],
        [0.50, "#ff4b4b"],  # 1: Gym (Red)
        [0.50, "#00ffcc"],
        [0.75, "#00ffcc"],  # 2: Swim (Cyan)
        [0.75, "#b042ff"],
        [1.00, "#b042ff"],  # 3: Gym+Swim (Purple)
    ]
    
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix.values,
            text=hover_text,
            hoverinfo="text",
            colorscale=colorscale,
            showscale=False,
            xgap=2,
            ygap=2,
            zmin=0,
            zmax=3,
        )
    )
    
    fig.update_layout(
        yaxis=dict(
            tickmode="array",
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            autorange="reversed",
            scaleanchor="x",
            scaleratio=1,
        ),
        xaxis=dict(showticklabels=False),
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=300,
    )
    
    return fig


def create_daily_tonnage_chart(merged_gym: pd.DataFrame) -> go.Figure:
    """
    Create a daily work capacity (tonnage) bar chart.
    
    Args:
        merged_gym: Merged DataFrame with gym_logs and exercise_sets data.
    
    Returns:
        go.Figure: Plotly bar chart figure.
    """
    if merged_gym.empty:
        fig = go.Figure()
        fig.add_annotation(text="Log workouts to build your streak.")
        return fig
    
    # Ensure tonnage column exists
    if "tonnage" not in merged_gym.columns:
        merged_gym["tonnage"] = merged_gym.get("weight", 0) * merged_gym.get("reps", 0)
    
    daily_tonnage = merged_gym.groupby("date")["tonnage"].sum().reset_index()
    
    fig = px.bar(
        daily_tonnage,
        x="date",
        y="tonnage",
        color="tonnage",
        color_continuous_scale="Tealgrn",
        title="Daily Work Capacity Streak",
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Total Volume (kg)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    
    return fig


def create_split_balance_radar(merged_gym: pd.DataFrame) -> go.Figure:
    """
    Create a radar chart showing split distribution of workout tonnage.
    
    Args:
        merged_gym: Merged DataFrame with gym_logs and exercise_sets data.
    
    Returns:
        go.Figure: Plotly radar chart figure.
    """
    if merged_gym.empty or "workout_type" not in merged_gym.columns:
        fig = go.Figure()
        fig.add_annotation(text="No workout data available.")
        return fig
    
    # Ensure tonnage column exists
    if "tonnage" not in merged_gym.columns:
        merged_gym["tonnage"] = merged_gym.get("weight", 0) * merged_gym.get("reps", 0)
    
    radar_data = merged_gym.groupby("workout_type")["tonnage"].sum().reset_index()
    
    if radar_data.empty:
        fig = go.Figure()
        fig.add_annotation(text="No split data available.")
        return fig
    
    fig = go.Figure(
        data=go.Scatterpolar(
            r=radar_data["tonnage"],
            theta=radar_data["workout_type"],
            fill="toself",
            line_color="#00ffcc",
        )
    )
    
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=False)),
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=350,
    )
    
    return fig


def create_weight_forecast(telemetry_df: pd.DataFrame) -> go.Figure:
    """
    Create a weight tracking chart with OLS regression forecast.
    Uses daily_telemetry with daily_weight column.
    
    Args:
        telemetry_df: DataFrame with daily_telemetry data (must have 'date' and 'daily_weight').
    
    Returns:
        go.Figure: Plotly figure with actual, moving average, and forecast lines.
    """
    if telemetry_df.empty or len(telemetry_df) < 3:
        fig = go.Figure()
        fig.add_annotation(
            text="Log at least 3 days of body weight data to generate the predictive model."
        )
        return fig
    
    body_df = telemetry_df.copy()
    
    # Ensure date column is datetime
    if "date" in body_df.columns:
        body_df["date"] = pd.to_datetime(body_df["date"])
    
    # Ensure daily_weight column exists and is numeric
    if "daily_weight" not in body_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for weight forecast.")
        return fig
    
    body_df["daily_weight"] = pd.to_numeric(body_df["daily_weight"], errors="coerce")
    body_df = body_df.dropna(subset=["daily_weight"])
    body_df = body_df.sort_values("date")
    
    if len(body_df) < 3:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient valid weight data for forecast.")
        return fig
    
    # Calculate 7-day rolling average
    body_df["7_Day_Avg"] = body_df["daily_weight"].rolling(window=7, min_periods=1).mean()
    
    # Linear Regression
    body_df["days_since_start"] = (body_df["date"] - body_df["date"].min()).dt.days
    z = np.polyfit(body_df["days_since_start"], body_df["daily_weight"], 1)
    p = np.poly1d(z)
    
    # Project 30 days into the future
    future_days = np.arange(body_df["days_since_start"].max(), body_df["days_since_start"].max() + 30)
    future_dates = pd.date_range(body_df["date"].max(), periods=30)
    future_weights = p(future_days)
    
    fig = go.Figure()
    
    # Actual Data
    fig.add_trace(
        go.Scatter(
            x=body_df["date"],
            y=body_df["daily_weight"],
            mode="lines",
            name="Daily Weight",
            line=dict(color="gray", width=1),
        )
    )
    
    # 7-Day Average
    fig.add_trace(
        go.Scatter(
            x=body_df["date"],
            y=body_df["7_Day_Avg"],
            mode="lines",
            name="7-Day Avg",
            line=dict(color="#00ffcc", width=3),
        )
    )
    
    # Forecast
    fig.add_trace(
        go.Scatter(
            x=future_dates,
            y=future_weights,
            mode="lines",
            name="30-Day Forecast",
            line=dict(color="red", width=2, dash="dash"),
        )
    )
    
    # Goal line
    fig.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="Goal: 80 kg")
    
    fig.update_layout(
        title="Current Trajectory vs. 30-Day Predictive Forecast",
        xaxis_title="Date",
        yaxis_title="Weight (kg)",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    
    return fig


def create_cardio_telemetry(swim_logs_df: pd.DataFrame, swim_sets_df: pd.DataFrame, telemetry_df: pd.DataFrame) -> go.Figure:
    """
    Create dual-axis chart for cardiovascular metrics (swim pace vs RHR).
    Joins swim_logs/swim_sets by log_id, calculates daily average pace,
    then merges with daily_telemetry to get RHR.
    
    Args:
        swim_logs_df: DataFrame with swim_logs data (date, log_id).
        swim_sets_df: DataFrame with swim_sets data (log_id, pace).
        telemetry_df: DataFrame with daily_telemetry data (date, rhr).
    
    Returns:
        go.Figure: Dual-axis Plotly figure or empty figure if insufficient data.
    """
    if swim_logs_df.empty or swim_sets_df.empty or telemetry_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="Insufficient data for cardio telemetry.")
        return fig
    
    # Join swim_logs and swim_sets on log_id
    swim_merged = pd.merge(swim_logs_df, swim_sets_df, on="log_id", how="left")
    
    if swim_merged.empty or "pace" not in swim_merged.columns:
        fig = go.Figure()
        fig.add_annotation(text="No valid swim pace data available.")
        return fig
    
    # Ensure pace is numeric
    swim_merged["pace"] = pd.to_numeric(swim_merged["pace"], errors="coerce")
    
    # Group by date to get daily average pace
    swim_daily = swim_merged.groupby("date").agg({"pace": "mean"}).reset_index()
    swim_daily = swim_daily[swim_daily["pace"] > 0]
    
    # Extract RHR from telemetry
    telemetry_df = telemetry_df.copy()
    telemetry_df["date"] = pd.to_datetime(telemetry_df["date"])
    telemetry_df["rhr"] = pd.to_numeric(telemetry_df["rhr"], errors="coerce")
    telemetry_rhr = telemetry_df[["date", "rhr"]].dropna(subset=["rhr"])
    
    # Merge on date
    cardio_df = pd.merge(swim_daily, telemetry_rhr, on="date", how="inner")
    
    if cardio_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No matching swim and recovery data.")
        return fig
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=cardio_df["date"],
            y=cardio_df["pace"],
            mode="lines+markers",
            name="Swim Pace (min/m)",
            line=dict(color="cyan", width=2),
            yaxis="y1",
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=cardio_df["date"],
            y=cardio_df["rhr"],
            mode="lines+markers",
            name="RHR (bpm)",
            line=dict(color="red", width=2),
            yaxis="y2",
        )
    )
    
    fig.update_layout(
        title="Cardiovascular Engine (Pace vs. RHR)",
        xaxis_title="Date",
        yaxis=dict(
            title=dict(text="Pace (min/m)", font=dict(color="cyan")),
            tickfont=dict(color="cyan"),
            side="left",
        ),
        yaxis2=dict(
            title=dict(text="RHR (bpm)", font=dict(color="red")),
            tickfont=dict(color="red"),
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    
    return fig


def create_metabolic_intake_chart(nut_df: pd.DataFrame) -> go.Figure:
    """
    Create metabolic intake (calories) line chart with rolling average.
    Uses total_calories from nutrition_logs.
    
    Args:
        nut_df: DataFrame with nutrition_logs data (must have 'date' and 'total_calories').
    
    Returns:
        go.Figure: Plotly figure with actual and 7-day average calories.
    """
    if nut_df.empty or "total_calories" not in nut_df.columns:
        fig = go.Figure()
        fig.add_annotation(text="No nutrition data available.")
        return fig
    
    nut_df = nut_df.copy()
    nut_df["total_calories"] = pd.to_numeric(nut_df["total_calories"], errors="coerce")
    nut_df = nut_df.dropna(subset=["total_calories"])
    
    if nut_df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No valid calorie data available.")
        return fig
    
    nut_df["Cal_7_Day_Avg"] = nut_df["total_calories"].rolling(window=7, min_periods=1).mean()
    
    fig = px.line(
        nut_df,
        x="date",
        y=["total_calories", "Cal_7_Day_Avg"],
        title="Metabolic Intake",
        color_discrete_sequence=["gray", "#00ffcc"],
        labels={"value": "Calories (kcal)", "variable": "Metric"},
    )
    
    fig.add_hline(
        y=3000, line_dash="dash", line_color="orange", annotation_text="Surplus Target (3000 kcal)"
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Calories (kcal)",
        hovermode="x unified",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    
    return fig


def get_max_1rm(merged_gym: pd.DataFrame, exercise_name: str) -> str:
    """
    Extract the maximum estimated 1RM for a given exercise.
    
    Args:
        merged_gym: Merged DataFrame with gym_logs and exercise_sets data including 'est_1rm' column.
        exercise_name: Name of the exercise to search for.
    
    Returns:
        str: Formatted maximum 1RM or "--" if not found.
    """
    if merged_gym.empty or "exercise" not in merged_gym.columns:
        return "--"
    
    if exercise_name not in merged_gym["exercise"].values:
        return "--"
    
    if "est_1rm" not in merged_gym.columns:
        return "--"
    
    max_val = merged_gym[merged_gym["exercise"] == exercise_name]["est_1rm"].max()
    
    if pd.isna(max_val) or max_val <= 0:
        return "--"
    
    return f"{round(max_val, 1)} kg"
