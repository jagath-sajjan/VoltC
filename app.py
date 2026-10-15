import streamlit as st
import cv2
import pandas as pd
from twin import create_floor_plan, load_data
from detector import RoomDetector
from rules import EnergyRulesEngine

# Page config must be the first Streamlit command
st.set_page_config(page_title="Nachos Digital Twin", layout="wide")

st.title("Digital Twin: Nachos HQ Monitor")
st.markdown("Live energy waste detection and visualization platform.")

# Load static data
rooms_data, state_data = load_data()
floors = sorted(list(set(r["floor"] for r in rooms_data["rooms"])))

# --- SIDEBAR ---
st.sidebar.header("Building Navigation")
selected_floor = st.sidebar.selectbox("Select Floor Level", floors)

# Filter rooms for the selected floor to power the dropdown
floor_rooms = {r["name"]: r for r in rooms_data["rooms"] if r["floor"] == selected_floor}
st.sidebar.markdown("---")
st.sidebar.subheader("Live Camera Feed")
selected_room_name = st.sidebar.selectbox("Select Room Camera", list(floor_rooms.keys()))
selected_room = floor_rooms[selected_room_name]

# Changed to a checkbox with value=True so it auto-runs on website load
start_feed = st.sidebar.checkbox("▶ Auto-Run Live Detection", value=True)

# --- MAIN DASHBOARD ---
col1, col2 = st.columns([2, 1.2])

with col1:
    st.subheader("Floor Plan")
    map_placeholder = st.empty()
    
    # Draw initial map with a unique key
    fig = create_floor_plan(selected_floor)
    map_placeholder.plotly_chart(fig, use_container_width=True, key="initial_map")

    st.subheader("Live Room Status")
    table_placeholder = st.empty()
    
    # Draw initial table
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
        # Initialize backend engines
        detector = RoomDetector(brightness_threshold=75.0)
        engine = EnergyRulesEngine()
        
        cap = cv2.VideoCapture(selected_room["clip"])
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        sample_step = 10
        interval_seconds = sample_step / fps
        
        frame_idx = 0
        
        # Streamlit processing loop
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % sample_step == 0:
                # 1. Run ML & Rules
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
                
                # 2. Update State JSON
                state_data[selected_room["id"]] = room_state
                engine.save_state(state_data)
                
                # 3. Draw bounding boxes and text on the frame
                color = (0, 255, 0) if stats["lights_on"] else (0, 0, 255)
                cv2.putText(frame, f"People: {stats['person_count']} | Light: {'ON' if stats['lights_on'] else 'OFF'}", 
                            (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                
                # Streamlit requires RGB color space, OpenCV uses BGR
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)
                
                # 4. Update the live metrics widget
                alert_color = "red" if room_state["status"] == "WASTE" else "green"
                metrics_placeholder.markdown(f"**Status:** :{alert_color}[{room_state['status']}] | **Waste Cost:** ₹{room_state['cost_inr_wasted']:.4f}")
                
            frame_idx += 1
            
        cap.release()
        
        # When video finishes, redraw the map and table with the new data and a unique key
        fig_final = create_floor_plan(selected_floor)
        map_placeholder.plotly_chart(fig_final, use_container_width=True, key="final_map")
        
        floor_state = [data for r_id, data in state_data.items() if r_id in floor_room_ids]
        table_placeholder.dataframe(pd.DataFrame(floor_state), use_container_width=True)