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

st.set_page_config(page_title="Live Webcam Feed", layout="wide")

rooms_data, state_data = load_data()

# --- SIDEBAR: Room selector ---
st.sidebar.header("Webcam Settings")
all_rooms  = rooms_data["rooms"]
room_names = [r["name"] for r in all_rooms]
selected_room_name = st.sidebar.selectbox("Assign Feed to Room", room_names)
selected_room      = next(r for r in all_rooms if r["name"] == selected_room_name)

st.title("Live Webcam Feed")
st.markdown(
    f"Room assignment: **{selected_room_name}**  —  "
    "click **START** below, then allow camera in the browser prompt."
)
st.markdown("---")


# ---------------------------------------------------------------------------
# VIDEO PROCESSOR  (runs in WebRTC thread, not Streamlit thread)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# CAMERA DEVICE ENUMERATION via JS → query params
# ---------------------------------------------------------------------------
# The browser exposes real camera labels only after getUserMedia permission.
# We inject a tiny JS snippet that:
#   1. Triggers the permission prompt
#   2. Enumerates videoinput devices
#   3. Writes labels+ids into the page URL as query params
# On the next Streamlit rerun those params are read and stored in session_state.
# ---------------------------------------------------------------------------

CAM_ENUM_JS = """
<script>
(async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({video: true, audio: false});
        stream.getTracks().forEach(t => t.stop());          // release immediately

        const devices = await navigator.mediaDevices.enumerateDevices();
        const vDevs   = devices.filter(d => d.kind === 'videoinput');

        const labels  = vDevs.map((d, i) => d.label || 'Camera ' + i);
        const ids     = vDevs.map(d => d.deviceId);

        // Persist in query string so Streamlit picks them up on rerun
        const params = new URLSearchParams(window.parent.location.search);
        const prev   = params.get('cam_labels');
        if (prev !== JSON.stringify(labels)) {
            params.set('cam_labels', JSON.stringify(labels));
            params.set('cam_ids',    JSON.stringify(ids));
            window.parent.history.replaceState({}, '', '?' + params.toString());
            // Trigger a Streamlit rerun so the sidebar dropdown refreshes
            window.parent.dispatchEvent(new Event('popstate'));
        }
    } catch (e) {
        console.warn('Camera enumeration failed:', e);
    }
})();
</script>
"""

# Render JS (height=0 keeps it invisible)
components.html(CAM_ENUM_JS, height=0)

# Read camera info from query params
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

# Fall back to a sane default on first load before JS runs
cam_labels = st.session_state.get("cam_labels", ["Default Camera"])
cam_ids    = st.session_state.get("cam_ids",    [""])

# Sidebar dropdown populated with real device names
selected_cam_label = st.sidebar.selectbox("Camera Device", cam_labels)
selected_cam_idx   = cam_labels.index(selected_cam_label)
selected_cam_id    = cam_ids[selected_cam_idx] if selected_cam_idx < len(cam_ids) else ""

# Pin to a specific deviceId when available; otherwise let the browser decide
video_constraints = (
    {"deviceId": {"exact": selected_cam_id}}
    if selected_cam_id else True
)

# Dynamic key: any change in room or camera tears down the old WebRTC peer
# and starts a fresh one — this is what makes device switching actually work.
streamer_key = f"webcam-{selected_room_name}-{selected_cam_idx}"

# ---------------------------------------------------------------------------
# LAYOUT
# ---------------------------------------------------------------------------
feed_col, data_col = st.columns([2, 1])

with feed_col:
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
    st.subheader("Live Telemetry")
    m_people = st.empty()
    m_light  = st.empty()
    m_status = st.empty()
    m_cost   = st.empty()
    st.markdown("---")
    st.subheader("All Room States")
    tbl = st.empty()


# ---------------------------------------------------------------------------
# METRIC REFRESH  (polls processor state each rerun)
# ---------------------------------------------------------------------------
if ctx.video_processor:
    with ctx.video_processor._lock:
        stats      = dict(ctx.video_processor.last_stats)
        room_state = dict(ctx.video_processor.last_state)

    if stats and room_state:
        m_people.metric("People Detected", stats.get("person_count", 0))
        m_light.metric("Lights",           "ON" if stats.get("lights_on") else "OFF")
        alert = "red" if room_state.get("status") in ["WASTE", "INEFFICIENT"] else "green"
        m_status.markdown(
            f"**Status** &nbsp; :{alert}[**{room_state.get('status', '—')}**]"
        )
        m_cost.metric("Waste Cost", f"Rs {room_state.get('cost_inr_wasted', 0):.4f}")

        state_data[selected_room["id"]] = room_state
        ctx.video_processor._engine.save_state(state_data)

        all_states = list(state_data.values())
        if all_states:
            tbl.dataframe(pd.DataFrame(all_states), use_container_width=True)

    # Keep metrics panel refreshing while stream is live
    import time
    time.sleep(0.4)
    st.rerun()
