import streamlit as st
import streamlit.components.v1 as components
import threading
import json as _json
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration
import av
import cv2

from twin import load_data
from detector import RoomDetector
from rules import EnergyRulesEngine
from overlay import draw_overlay
from styles import inject_styles

st.set_page_config(page_title="VoltC — Live Feed", layout="wide")
inject_styles()

rooms_data, state_data = load_data()


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="volt-wordmark">Volt<span>C</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.65rem;color:#333;letter-spacing:0.1em;'
        'text-transform:uppercase;margin-bottom:1.5rem">Building Intelligence</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="volt-section-header">Navigation</div>', unsafe_allow_html=True)
    st.page_link("app.py",              label="Overview")
    st.page_link("pages/Webcam_Feed.py", label="Live Webcam")

    all_rooms  = rooms_data["rooms"]
    room_names = [r["name"] for r in all_rooms]

    st.markdown('<div class="volt-section-header">Room</div>', unsafe_allow_html=True)
    selected_room_name = st.selectbox("Room", room_names, label_visibility="collapsed")
    selected_room = next(r for r in all_rooms if r["name"] == selected_room_name)

    st.markdown('<div class="volt-section-header">Camera Device</div>', unsafe_allow_html=True)


# ── TOPBAR ────────────────────────────────────────────────────────────────────
from datetime import datetime
now_str = datetime.now().strftime("%d %b  %H:%M")

st.markdown(
    f'''
    <div class="volt-topbar">
        <div>
            <span style="font-family:Inter;font-size:1.1rem;font-weight:600;
                         color:#fff;letter-spacing:-0.01em">Live Webcam</span>
            <span style="font-family:Inter;font-size:0.75rem;color:#444;
                         margin-left:1rem">{selected_room_name}</span>
        </div>
        <div style="display:flex;align-items:center;gap:1.5rem">
            <span class="volt-timestamp">{now_str}</span>
            <span><span class="volt-live-dot"></span>
            <span class="volt-live-label">WebRTC</span></span>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ── VIDEO PROCESSOR ───────────────────────────────────────────────────────────
class RoomVideoProcessor(VideoProcessorBase):
    def __init__(self):
        self._detector = RoomDetector(
            brightness_threshold=selected_room.get("brightness_threshold", 75.0)
        )
        self._engine   = EnergyRulesEngine()
        self._room     = selected_room
        self._lock     = threading.Lock()
        self.last_stats  = {}
        self.last_state  = {}

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")

        stats = self._detector.analyze_frame(img)
        room_state = self._engine.evaluate_room(
            room_id              = self._room["id"],
            room_name            = self._room["name"],
            person_count         = stats["person_count"],
            lights_on            = stats["lights_on"],
            appliances_active    = self._room["appliances"],
            interval_seconds     = 1 / 30.0,
            grace_period_seconds = 2.0,
        )

        with self._lock:
            self.last_stats = stats
            self.last_state = room_state

        img = draw_overlay(img, stats, room_state)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ── CAMERA DEVICE ENUMERATION ─────────────────────────────────────────────────
CAM_ENUM_JS = """
<script>
(async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
        stream.getTracks().forEach(t => t.stop());
        const devices = await navigator.mediaDevices.enumerateDevices();
        const vDevs   = devices.filter(d => d.kind === 'videoinput');
        const labels  = vDevs.map((d, i) => d.label || 'Camera ' + i);
        const ids     = vDevs.map(d => d.deviceId);
        const params  = new URLSearchParams(window.parent.location.search);
        if (params.get('cam_labels') !== JSON.stringify(labels)) {
            params.set('cam_labels', JSON.stringify(labels));
            params.set('cam_ids',    JSON.stringify(ids));
            window.parent.history.replaceState({}, '', '?' + params.toString());
            window.parent.dispatchEvent(new Event('popstate'));
        }
    } catch (e) { console.warn('Camera enumeration failed:', e); }
})();
</script>
"""
components.html(CAM_ENUM_JS, height=0)

qp = st.query_params
cam_labels_raw = qp.get("cam_labels")
cam_ids_raw    = qp.get("cam_ids")

if cam_labels_raw:
    try:
        parsed_labels = _json.loads(cam_labels_raw)
        parsed_ids    = _json.loads(cam_ids_raw) if cam_ids_raw else []
        if parsed_labels:
            st.session_state["cam_labels"] = parsed_labels
            st.session_state["cam_ids"]    = parsed_ids
    except Exception:
        pass

cam_labels = st.session_state.get("cam_labels", ["Default Camera"])
cam_ids    = st.session_state.get("cam_ids",    [""])

with st.sidebar:
    selected_cam_label = st.selectbox("Device", cam_labels, label_visibility="collapsed")
    selected_cam_idx   = cam_labels.index(selected_cam_label)
    selected_cam_id    = cam_ids[selected_cam_idx] if selected_cam_idx < len(cam_ids) else ""

video_constraints = (
    {"deviceId": {"exact": selected_cam_id}} if selected_cam_id else True
)
streamer_key = f"webcam-{selected_room_name}-{selected_cam_idx}"


# ── LAYOUT ────────────────────────────────────────────────────────────────────
feed_col, data_col = st.columns([2, 1], gap="large")

with feed_col:
    st.markdown(
        '<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;'
        'color:#444;margin-bottom:0.5rem">Camera Feed</div>',
        unsafe_allow_html=True,
    )
    ctx = webrtc_streamer(
        key=streamer_key,
        video_processor_factory=RoomVideoProcessor,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        media_stream_constraints={"video": video_constraints, "audio": False},
        async_processing=True,
    )

with data_col:
    st.markdown(
        '<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;'
        'color:#444;margin-bottom:0.5rem">Live Telemetry</div>',
        unsafe_allow_html=True,
    )

    m_people = st.empty()
    m_light  = st.empty()
    m_status = st.empty()
    m_cost   = st.empty()

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:0.1em;'
        'color:#444;border-top:1px solid #1E1E1E;padding-top:1rem;margin-bottom:0.5rem">'
        'All Rooms</div>',
        unsafe_allow_html=True,
    )
    tbl = st.empty()


# ── METRIC REFRESH ────────────────────────────────────────────────────────────
if ctx.video_processor:
    with ctx.video_processor._lock:
        stats      = dict(ctx.video_processor.last_stats)
        room_state = dict(ctx.video_processor.last_state)

    if stats and room_state:
        status       = room_state.get("status", "UNKNOWN")
        status_color = "#E53E3E" if status in ("WASTE", "INEFFICIENT") else "#AAAAAA"
        cost         = room_state.get("cost_inr_wasted", 0)
        people       = stats.get("person_count", 0)
        lights       = "ON" if stats.get("lights_on") else "OFF"

        m_people.markdown(
            f'''<div class="volt-stat" style="margin-bottom:1px">
                <div class="label">People Detected</div>
                <div class="value">{people}</div>
            </div>''',
            unsafe_allow_html=True,
        )
        m_light.markdown(
            f'''<div class="volt-stat" style="margin-bottom:1px">
                <div class="label">Lighting</div>
                <div class="value" style="font-size:1.4rem">{lights}</div>
            </div>''',
            unsafe_allow_html=True,
        )
        m_status.markdown(
            f'''<div class="volt-stat" style="margin-bottom:1px">
                <div class="label">Status</div>
                <div class="value" style="font-size:1.2rem;color:{status_color}">{status}</div>
            </div>''',
            unsafe_allow_html=True,
        )
        m_cost.markdown(
            f'''<div class="volt-stat">
                <div class="label">Waste Cost</div>
                <div class="value" style="font-size:1.3rem;color:#E53E3E">Rs {cost:.4f}</div>
            </div>''',
            unsafe_allow_html=True,
        )

        state_data[selected_room["id"]] = room_state
        ctx.video_processor._engine.save_state(state_data)

        all_states = list(state_data.values())
        if all_states:
            df = pd.DataFrame(all_states)[
                ["room_name", "status", "person_count", "active_load_watts", "cost_inr_wasted"]
            ].rename(columns={
                "room_name": "Room",
                "status": "Status",
                "person_count": "People",
                "active_load_watts": "Load (W)",
                "cost_inr_wasted": "Waste (Rs)",
            })
            tbl.dataframe(df, use_container_width=True, hide_index=True)

    import time
    time.sleep(0.4)
    st.rerun()
