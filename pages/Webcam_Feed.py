import streamlit as st
import cv2
import pandas as pd
import sys
import os

# Let the page import sibling modules from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from twin import load_data
from detector import RoomDetector
from rules import EnergyRulesEngine
from overlay import draw_overlay

st.set_page_config(page_title="Live Webcam Feed", layout="wide")

rooms_data, state_data = load_data()

# --- SIDEBAR ---
st.sidebar.header("Webcam Settings")
all_rooms   = rooms_data["rooms"]
room_names  = [r["name"] for r in all_rooms]
selected_room_name = st.sidebar.selectbox("Assign Feed to Room", room_names)
selected_room      = next(r for r in all_rooms if r["name"] == selected_room_name)

# --- SESSION STATE ---
if "webcam_running" not in st.session_state:
    st.session_state.webcam_running = False

# --- HEADER ---
st.title("Live Webcam Feed")
st.markdown(f"Room assignment: **{selected_room_name}**")

btn_c1, btn_c2, _ = st.columns([1, 1, 4])
with btn_c1:
    if st.button("Start Feed", use_container_width=True,
                 disabled=st.session_state.webcam_running):
        st.session_state.webcam_running = True
        st.rerun()
with btn_c2:
    if st.button("Stop Feed", use_container_width=True,
                 disabled=not st.session_state.webcam_running):
        st.session_state.webcam_running = False
        st.rerun()

st.markdown("---")

# --- LAYOUT: feed left, live data right ---
feed_col, data_col = st.columns([2, 1])

with feed_col:
    feed_placeholder = st.empty()

with data_col:
    st.subheader("Live Telemetry")
    m_people = st.empty()
    m_light  = st.empty()
    m_status = st.empty()
    m_cost   = st.empty()
    st.markdown("---")
    st.subheader("All Room States")
    tbl = st.empty()

# --- WEBCAM LOOP: one frame per Streamlit rerun ---
if st.session_state.webcam_running:
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        st.session_state.webcam_running = False
        st.error(
            "**Cannot read from webcam.**\n\n"
            "On macOS, grant Camera access to Terminal:\n"
            "System Preferences > Security & Privacy > Camera "
            "> enable Terminal (or iTerm2), then restart the app."
        )
        st.stop()

    # Detect & evaluate
    detector   = RoomDetector(brightness_threshold=selected_room.get("brightness_threshold", 75.0))
    engine     = EnergyRulesEngine()

    stats = detector.analyze_frame(frame)
    room_state = engine.evaluate_room(
        room_id            = selected_room["id"],
        room_name          = selected_room["name"],
        person_count       = stats["person_count"],
        lights_on          = stats["lights_on"],
        appliances_active  = selected_room["appliances"],
        interval_seconds   = 1 / 30.0,
        grace_period_seconds = 2.0,
    )
    state_data[selected_room["id"]] = room_state
    engine.save_state(state_data)

    # Draw overlay + display
    frame     = draw_overlay(frame, stats, room_state)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    feed_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

    # Live metric cards
    m_people.metric("People Detected",  stats["person_count"])
    m_light.metric("Lights",            "ON" if stats["lights_on"] else "OFF")
    alert = "red" if room_state["status"] in ["WASTE", "INEFFICIENT"] else "green"
    m_status.markdown(f"**Status** &nbsp; :{alert}[**{room_state['status']}**]")
    m_cost.metric("Waste Cost",         f"Rs {room_state['cost_inr_wasted']:.4f}")

    all_states = list(state_data.values())
    if all_states:
        tbl.dataframe(pd.DataFrame(all_states), use_container_width=True)

    # Trigger next frame
    st.rerun()

else:
    feed_placeholder.info("Click 'Start Feed' to begin the live webcam stream.")
