import streamlit as st
import cv2
import pandas as pd
from twin import create_floor_plan, load_data
from detector import RoomDetector
from rules import EnergyRulesEngine
from report import generate_action_plan

st.set_page_config(page_title="Nachos Digital Twin", layout="wide")

st.title("Digital Twin: Nachos HQ Monitor")
st.markdown("Live energy waste detection and visualization platform.")

rooms_data, state_data = load_data()
floors = sorted(list(set(r["floor"] for r in rooms_data["rooms"])))

# --- SIDEBAR ---
st.sidebar.header("Building Navigation")
selected_floor = st.sidebar.selectbox("Select Floor Level", floors)

floor_rooms = {r["name"]: r for r in rooms_data["rooms"] if r["floor"] == selected_floor}
st.sidebar.markdown("---")
st.sidebar.subheader("Live Camera Feed")
selected_room_name = st.sidebar.selectbox("Select Room Camera", list(floor_rooms.keys()))
selected_room = floor_rooms[selected_room_name]

start_feed = st.sidebar.checkbox("Auto-Run Live Detection", value=True)

# --- MAIN DASHBOARD ---
col1, col2 = st.columns([2, 1.2])

with col1:
    st.subheader("Floor Plan")
    map_placeholder = st.empty()
    
    fig = create_floor_plan(selected_floor)
    map_placeholder.plotly_chart(fig, use_container_width=True, key="initial_map")

    st.subheader("Live Room Status")
    table_placeholder = st.empty()
    
    floor_room_ids = [r["id"] for r in rooms_data["rooms"] if r["floor"] == selected_floor]
    floor_state = [data for r_id, data in state_data.items() if r_id in floor_room_ids]
    if floor_state:
        table_placeholder.dataframe(pd.DataFrame(floor_state), use_container_width=True)
    else:
        table_placeholder.info("No live telemetry for this floor yet.")

with col2:
    st.subheader(f"Camera: {selected_room_name}")
    video_placeholder = st.empty()
    metrics_placeholder = st.empty()
    
    if not start_feed:
        video_placeholder.info("Check 'Auto-Run Live Detection' in the sidebar to connect to camera.")
        
    if start_feed:
        room_threshold = selected_room.get("brightness_threshold", 75.0)
        detector = RoomDetector(brightness_threshold=room_threshold)
        engine = EnergyRulesEngine()
        
        cap = cv2.VideoCapture(selected_room["clip"])
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        sample_step = 10
        interval_seconds = sample_step / fps
        
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % sample_step == 0:
                stats = detector.analyze_frame(frame)
                
                room_state = engine.evaluate_room(
                    room_id=selected_room["id"],
                    room_name=selected_room["name"],
                    person_count=stats["person_count"],
                    lights_on=stats["lights_on"],
                    appliances_active=selected_room["appliances"],
                    interval_seconds=interval_seconds,
                    grace_period_seconds=2.0
                )
                
                state_data[selected_room["id"]] = room_state
                engine.save_state(state_data)
                
                color = (0, 255, 0) if stats["lights_on"] else (0, 0, 255)
                cv2.putText(frame, f"People: {stats['person_count']} | Light: {'ON' if stats['lights_on'] else 'OFF'}", 
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                
                alert_color = "red" if room_state["status"] in ["WASTE", "INEFFICIENT"] else "green"
                metrics_placeholder.markdown(f"**Status:** :{alert_color}[{room_state['status']}] | **Waste Cost:** Rs {room_state['cost_inr_wasted']:.4f}")
                
            frame_idx += 1
            
        cap.release()
        
        fig_final = create_floor_plan(selected_floor)
        map_placeholder.plotly_chart(fig_final, use_container_width=True, key="final_map")
        
        floor_state = [data for r_id, data in state_data.items() if r_id in floor_room_ids]
        table_placeholder.dataframe(pd.DataFrame(floor_state), use_container_width=True)

# --- NEW: ANALYTICS & AI REPORTING ---
st.markdown("---")
st.header("Analytics & AI Insights")

col3, col4 = st.columns([1, 1])

with col3:
    st.subheader("What-If Simulator")
    st.info("Simulate monthly impact if motion-based auto-off sensors were installed.")
    
    daily_waste_hours = st.slider("Estimated daily waste per room (hours)", 1, 10, 4)
    active_rooms = len(state_data) if state_data else 1
    
    monthly_kwh = active_rooms * 2.0 * daily_waste_hours * 22 
    monthly_inr = monthly_kwh * 9.50 
    monthly_co2 = monthly_kwh * 0.71
    
    st.success(f"**Projected Monthly Savings:** Rs {monthly_inr:,.2f}")
    st.warning(f"**Carbon Footprint Reduction:** {monthly_co2:,.1f} kg CO2")

with col4:
    st.subheader("GenAI Action Plan")
    if st.button("Generate Facility Report"):
        with st.spinner("Querying Gemini..."):
            report_text = generate_action_plan(state_data)
            st.markdown(report_text)