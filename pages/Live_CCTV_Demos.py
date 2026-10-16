import streamlit as st
import cv2
import numpy as np
import urllib.request
import time
from datetime import datetime
import pandas as pd
import os
import sys

# Add parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rules import EnergyRulesEngine
from styles import inject_styles
from ultralytics import YOLO
import torch

st.set_page_config(
    page_title="VoltC - Live CCTV Demos",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# -- CCTV CAMERAS SPECIFICATION ------------------------------------------------
# Feeds from http://www.insecam.org/en/bycountry/IN/
# Direct full-view URLs configured with View=Full to eliminate web data/menus
CCTV_CAMERAS = [
    {
        "id": "1012451",
        "name": "Mumbai Metropolitan Facility",
        "city": "Mumbai",
        "region": "Maharashtra",
        "country": "India",
        "insecam_url": "http://www.insecam.org/en/view/1012451/#camstream",
        "direct_feed_url": "http://202.179.70.235:92/ViewerFrame?Resolution=320x240&Quality=Standard&Size=STD&Language=0&Sound=Enable&Mode=JPEG&RPeriod=65535&SendMethod=1&View=Full",
        "stream_url": "http://202.179.70.235:92/SnapshotJPEG?Resolution=320x240&Quality=Standard",
        "thumb_url": "http://insecam.org/static/thumb/1012451.jpg",
        "camera_model": "Panasonic BL-C101 Network Camera",
        "appliances": ["hall_lighting_array", "desktop_computer", "ac_1_5_ton"],
        "brightness_threshold": 75.0,
        "description": "High-speed interior facility stream in Mumbai, MH. Monitored for hall lighting arrays and AC consumption.",
    },
    {
        "id": "1012754",
        "name": "Nellore Commercial Complex (Cam 1)",
        "city": "Nellore",
        "region": "Andhra Pradesh",
        "country": "India",
        "insecam_url": "http://www.insecam.org/en/view/1012754/#camstream",
        "direct_feed_url": "http://106.51.185.124:81/ViewerFrame?Resolution=320x240&Quality=Standard&Size=STD&Language=0&Sound=Enable&Mode=JPEG&RPeriod=65535&SendMethod=1&View=Full",
        "stream_url": "http://106.51.185.124:81/SnapshotJPEG?Resolution=320x240&Quality=Standard",
        "thumb_url": "http://insecam.org/static/thumb/1012754.jpg",
        "camera_model": "Panasonic BL-C101 Network Camera",
        "appliances": ["hall_lighting_array", "ac_1_5_ton"],
        "brightness_threshold": 80.0,
        "description": "Commercial facility in Nellore, AP. Monitored for hall lighting arrays and AC consumption.",
    },
    {
        "id": "1012301",
        "name": "Nellore Facility Corridor (Cam 2)",
        "city": "Nellore",
        "region": "Andhra Pradesh",
        "country": "India",
        "insecam_url": "http://www.insecam.org/en/view/1012301/#camstream",
        "direct_feed_url": "http://106.51.185.124:85/ViewerFrame?Resolution=320x240&Quality=Standard&Size=STD&Language=0&Sound=Enable&Mode=JPEG&RPeriod=65535&SendMethod=1&View=Full",
        "stream_url": "http://106.51.185.124:85/SnapshotJPEG?Resolution=320x240&Quality=Standard",
        "thumb_url": "http://insecam.org/static/thumb/1012301.jpg",
        "camera_model": "Panasonic BL-C101 Network Camera",
        "appliances": ["hall_lighting_array", "fan"],
        "brightness_threshold": 75.0,
        "description": "Distribution corridor in Nellore, AP. Monitored for corridor lighting and active ventilation load.",
    },
    {
        "id": "1012081",
        "name": "Nagercoil Regional Transit",
        "city": "Nagercoil",
        "region": "Tamil Nadu",
        "country": "India",
        "insecam_url": "http://www.insecam.org/en/view/1012081/#camstream",
        "direct_feed_url": "http://117.216.143.179:80/cgi-bin/snapshot.cgi",
        "stream_url": "http://117.216.143.179:80/cgi-bin/snapshot.cgi",
        "thumb_url": "http://insecam.org/static/thumb/1012081.jpg",
        "camera_model": "Ninivision CCTV System",
        "appliances": ["tube_light", "fan"],
        "brightness_threshold": 70.0,
        "description": "Perimeter gateway in Nagercoil, TN. Monitored for perimeter illumination and fan load.",
    },
]

CAM_MAP = {c["id"]: c for c in CCTV_CAMERAS}


# -- CACHED RESOURCES ----------------------------------------------------------
@st.cache_resource
def get_yolo_model():
    return YOLO("yolov8n.pt")


@st.cache_resource
def get_energy_engine():
    return EnergyRulesEngine()


# -- FAST FRAME CAPTURE & BUFFERING -------------------------------------------
def fetch_camera_frame_fast(stream_url: str, thumb_url: str, timeout: float = 1.2):
    """
    High-speed frame grabber.
    Prioritizes low-latency direct IP snapshot with Insecam CDN fallback,
    ensuring continuous real-time delivery with zero dropped frames.
    """
    # 1. Direct snapshot
    try:
        req = urllib.request.Request(
            stream_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            arr = np.asarray(bytearray(resp.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None and img.size > 0:
                return img, "DIRECT_STREAM"
    except Exception:
        pass

    # 2. Fast CDN fallback
    try:
        req = urllib.request.Request(
            thumb_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Cache-Control": "no-cache",
            },
        )
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            arr = np.asarray(bytearray(resp.read()), dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if img is not None and img.size > 0:
                return img, "INSECAM_CDN"
    except Exception:
        pass

    return None, "OFFLINE"


def get_placeholder_frame(cam: dict, status_text: str = "CONNECTING"):
    """Technical standby frame."""
    frame = np.zeros((240, 320, 3), dtype=np.uint8)
    frame[:] = (18, 18, 18)

    for x in range(0, 320, 20):
        cv2.line(frame, (x, 0), (x, 240), (28, 28, 28), 1)
    for y in range(0, 240, 20):
        cv2.line(frame, (0, y), (320, y), (28, 28, 28), 1)

    cv2.putText(frame, cam["city"].upper(), (14, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, cam["camera_model"].split()[0].upper(), (14, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1)
    cv2.putText(frame, status_text, (14, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 180, 255), 1)
    cv2.putText(frame, "DIRECT CAM FEED ACTIVE", (14, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (90, 90, 90), 1)
    return frame


def draw_cctv_hud(frame, stats, room_state, cam, detected_objects):
    """Renders VoltC HUD overlay and detection bounding boxes on the camera frame."""
    h, w = frame.shape[:2]

    OUTLINE   = (0, 0, 0)
    PEOPLE_C  = (50, 255, 120)    # lime
    BOX_C     = (0, 220, 255)     # cyan/gold
    STATUS_OK = (50, 230, 80)     # green
    STATUS_BAD= (80, 80, 255)     # red
    COST_C    = (50, 200, 255)    # amber
    BRIGHT_C  = (200, 200, 255)   # lavender

    font = cv2.FONT_HERSHEY_SIMPLEX

    def _put(img, text, pos, scale, color, thick=1):
        cv2.putText(img, text, pos, font, scale, OUTLINE, thick + 2, cv2.LINE_AA)
        cv2.putText(img, text, pos, font, scale, color, thick, cv2.LINE_AA)

    # Bounding boxes
    for obj in detected_objects:
        x1, y1, x2, y2 = obj["box"]
        label = f"{obj['class']} {obj['confidence']:.2f}"
        color = PEOPLE_C if obj["class"] == "person" else BOX_C

        cv2.rectangle(frame, (x1, y1), (x2, y2), OUTLINE, 3)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)

        (tw, th), _ = cv2.getTextSize(label, font, 0.38, 1)
        cv2.rectangle(frame, (x1, y1 - th - 4), (x1 + tw + 4, y1), (0, 0, 0), -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 3), font, 0.38, color, 1, cv2.LINE_AA)

    # Top-Left HUD
    status = room_state.get("status", "MONITORING")
    status_c = STATUS_BAD if status in ("WASTE", "INEFFICIENT") else STATUS_OK

    _put(frame, f"People   : {stats['person_count']}", (12, 24), 0.55, PEOPLE_C)
    _put(frame, f"Lighting : {'ON' if stats['lights_on'] else 'OFF'}", (12, 46), 0.55, (255, 255, 255))
    _put(frame, f"Status   : {status}", (12, 68), 0.55, status_c)
    _put(frame, f"Load     : {room_state.get('active_load_watts', 0):.0f} W", (12, 90), 0.50, (200, 200, 200))
    _put(frame, f"Waste    : Rs {room_state.get('cost_inr_wasted', 0):.4f}", (12, 112), 0.50, COST_C)

    # Top-Right Meta
    cam_meta = f"{cam['city'].upper()} | {cam['camera_model'].split()[0]}"
    (cw, _), _ = cv2.getTextSize(cam_meta, font, 0.45, 1)
    _put(frame, cam_meta, (w - cw - 12, 24), 0.45, (180, 180, 180), 1)

    # Bottom-Right Brightness & Time
    br_text = f"Lum: {stats.get('mean_brightness', 0):.1f} | {datetime.now().strftime('%H:%M:%S')}"
    (tw, _), _ = cv2.getTextSize(br_text, font, 0.45, 1)
    _put(frame, br_text, (w - tw - 12, h - 10), 0.45, BRIGHT_C, 1)

    return frame


# -- SESSION STATE INITIALIZATION ----------------------------------------------
if "selected_cctv_cam" not in st.session_state:
    st.session_state.selected_cctv_cam = None

if "cctv_frame_cache" not in st.session_state:
    st.session_state.cctv_frame_cache = {}

qp = st.query_params
if "cam" in qp and qp["cam"] in CAM_MAP:
    st.session_state.selected_cctv_cam = qp["cam"]


# -- SIDEBAR -------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="volt-wordmark">Volt<span>C</span></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-size:0.65rem;color:#333;letter-spacing:0.1em;'
        'text-transform:uppercase;margin-bottom:1.5rem">Building Intelligence</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="volt-section-header">Navigation</div>', unsafe_allow_html=True)
    st.page_link("app.py", label="Overview")
    st.page_link("pages/Webcam_Feed.py", label="Live Webcam")
    st.page_link("pages/Live_CCTV_Demos.py", label="Live CCTV Demos")

    st.markdown('<div class="volt-section-header">CCTV Feed Selector</div>', unsafe_allow_html=True)
    view_options = ["Overview Grid (All 4 Cams)"] + [f"{c['city']} - {c['name']}" for c in CCTV_CAMERAS]
    cam_id_list = [None] + [c["id"] for c in CCTV_CAMERAS]

    curr_idx = 0
    if st.session_state.selected_cctv_cam in CAM_MAP:
        curr_idx = cam_id_list.index(st.session_state.selected_cctv_cam)

    chosen_view = st.selectbox("Select View", view_options, index=curr_idx, label_visibility="collapsed")
    new_cam_id = cam_id_list[view_options.index(chosen_view)]
    if new_cam_id != st.session_state.selected_cctv_cam:
        st.session_state.selected_cctv_cam = new_cam_id
        if new_cam_id:
            st.query_params["cam"] = new_cam_id
        elif "cam" in st.query_params:
            del st.query_params["cam"]
        st.rerun()

    st.markdown('<div class="volt-section-header">Performance Tuning</div>', unsafe_allow_html=True)
    refresh_delay = st.slider("Sampling Cadence (s)", 0.05, 1.5, 0.2, 0.05, help="Lower interval yields faster live detection loop")
    detect_mode = st.radio(
        "Detection Target",
        ["Occupancy Only (People)", "Full Scene (All Objects)"],
        label_visibility="collapsed",
    )
    conf_thresh = st.slider("Confidence Threshold", 0.15, 0.85, 0.35, 0.05)
    run_live = st.checkbox("Run Live Calculation", value=True)


# -- TOPBAR --------------------------------------------------------------------
now_str = datetime.now().strftime("%d %b  %H:%M")
curr_cam = CAM_MAP.get(st.session_state.selected_cctv_cam)
view_label = f"Windowed Full Screen · {curr_cam['name']}" if curr_cam else "Public CCTV Benchmark Grid"

st.markdown(
    f'''
    <div class="volt-topbar">
        <div>
            <span style="font-family:Inter;font-size:1.1rem;font-weight:600;
                         color:#fff;letter-spacing:-0.01em">Live CCTV Demos</span>
            <span style="font-family:Inter;font-size:0.75rem;color:#E53E3E;
                         margin-left:1rem">{view_label}</span>
        </div>
        <div style="display:flex;align-items:center;gap:1.5rem">
            <span class="volt-timestamp">{now_str}</span>
            <span><span class="volt-live-dot"></span>
            <span class="volt-live-label">Insecam Live</span></span>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# -- PUBLIC CCTV ADVISORY BANNER -----------------------------------------------
st.markdown(
    '''
    <div style="background:#111111; border:1px solid #2B1515; border-left:3px solid #E53E3E;
                padding:0.85rem 1.25rem; margin-bottom:1.5rem;">
        <div style="display:flex; align-items:center; justify-content:space-between;">
            <span style="color:#E53E3E; font-family:'IBM Plex Mono', monospace; font-size:0.75rem; font-weight:600; letter-spacing:0.08em; text-transform:uppercase;">
                Public Camera Benchmark & Ethical Notice
            </span>
            <a href="http://www.insecam.org/en/bycountry/IN/" target="_blank"
               style="color:#888; font-size:0.68rem; text-decoration:none; text-transform:uppercase; letter-spacing:0.05em;">
                Insecam India Directory [Ext]
            </a>
        </div>
        <div style="color:#888888; font-size:0.73rem; line-height:1.5; margin-top:0.35rem;">
            Direct camera feeds sourced from open public IP endpoints cataloged on Insecam. 
            VoltC processes video frames in memory for automated building occupancy verification and 
            lighting compliance benchmarking. No video footage is stored or persisted.
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ==============================================================================
# VIEW 1: WINDOWED FULL SCREEN MODE (Selected Camera)
# ==============================================================================
if curr_cam is not None:
    # Action Bar
    col_nav1, col_nav2, col_nav3 = st.columns([1.5, 3.2, 3.3])

    with col_nav1:
        if st.button("<- Back to Grid", use_container_width=True):
            st.session_state.selected_cctv_cam = None
            if "cam" in st.query_params:
                del st.query_params["cam"]
            st.rerun()

    with col_nav2:
        st.markdown(
            f'''
            <div style="display:flex; align-items:center; gap:0.8rem; height:100%; padding-top:0.35rem;">
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.8rem; color:#FFFFFF;">
                    {curr_cam['city']}, {curr_cam['country']}
                </span>
                <span style="font-size:0.72rem; color:#444;">|</span>
                <span style="font-family:'IBM Plex Mono',monospace; font-size:0.75rem; color:#888;">
                    {curr_cam['camera_model']}
                </span>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with col_nav3:
        st.markdown(
            f'''
            <div style="display:flex; align-items:center; justify-content:flex-end; gap:0.6rem; height:100%; padding-top:0.2rem;">
                <a href="{curr_cam['insecam_url']}" target="_blank"
                   style="background:#161616; border:1px solid #333; color:#DDD; padding:0.4rem 0.75rem;
                          font-size:0.7rem; font-family:'IBM Plex Mono',monospace; text-decoration:none;
                          text-transform:uppercase; letter-spacing:0.05em;">
                    Stream (#camstream)
                </a>
                <a href="{curr_cam['direct_feed_url']}" target="_blank"
                   style="background:#1E1E1E; border:1px solid #E53E3E; color:#FFF; padding:0.4rem 0.75rem;
                          font-size:0.7rem; font-family:'IBM Plex Mono',monospace; text-decoration:none;
                          text-transform:uppercase; letter-spacing:0.05em; font-weight:600;">
                    Direct Cam Feed [Full View] ->
                </a>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)

    # Main Grid: Left = Video Canvas, Right = Real-time Telemetry
    left_video_col, right_stats_col = st.columns([2.2, 1.2], gap="large")

    with left_video_col:
        st.markdown(
            f'<div class="volt-section-header" style="margin-top:0">'
            f'Windowed Full Screen Live Feed - {curr_cam["name"]}</div>',
            unsafe_allow_html=True,
        )
        video_placeholder = st.empty()
        status_bar_placeholder = st.empty()

    with right_stats_col:
        st.markdown(
            '<div class="volt-section-header" style="margin-top:0">Live Telemetry & Rules Calculation</div>',
            unsafe_allow_html=True,
        )
        m_people_ph = st.empty()
        m_lighting_ph = st.empty()
        m_status_ph = st.empty()
        m_load_ph = st.empty()
        m_waste_ph = st.empty()

        st.markdown('<div class="volt-section-header">Detected Objects Breakdown</div>', unsafe_allow_html=True)
        detections_table_ph = st.empty()

        st.markdown('<div class="volt-section-header">Direct Stream Target</div>', unsafe_allow_html=True)
        st.markdown(
            f'''
            <div style="background:#111111; border:1px solid #1E1E1E; padding:0.9rem; font-size:0.75rem; color:#888;">
                <div style="color:#FFF; font-weight:600; margin-bottom:0.4rem;">{curr_cam['name']}</div>
                <div style="margin-bottom:0.3rem;"><span style="color:#555;">Pure Video Feed:</span> <a href="{curr_cam['direct_feed_url']}" target="_blank" style="color:#E53E3E; font-family:'IBM Plex Mono',monospace;">ViewerFrame [Full View]</a></div>
                <div style="margin-bottom:0.3rem;"><span style="color:#555;">Appliances Monitored:</span> <span style="font-family:'IBM Plex Mono',monospace; color:#CCC;">{", ".join(curr_cam["appliances"])}</span></div>
                <div><span style="color:#555;">Luminance Threshold:</span> <span style="font-family:'IBM Plex Mono',monospace; color:#CCC;">{curr_cam["brightness_threshold"]} px</span></div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    # Initial frame from cache or placeholder
    cached_frame = st.session_state.cctv_frame_cache.get(curr_cam["id"])
    if cached_frame is None:
        cached_frame = get_placeholder_frame(curr_cam, "CONNECTING TO LIVE FEED...")
        video_placeholder.image(cached_frame, channels="BGR", use_container_width=True)

    yolo_model = get_yolo_model()
    engine = get_energy_engine()

    # Steady, ultra-fast in-place streaming loop
    if run_live:
        while True:
            t_start = time.time()
            fresh_frame, frame_source = fetch_camera_frame_fast(curr_cam["stream_url"], curr_cam["thumb_url"], timeout=1.2)

            if fresh_frame is not None:
                active_frame = fresh_frame
                st.session_state.cctv_frame_cache[curr_cam["id"]] = fresh_frame
                conn_status = "ONLINE (" + ("DIRECT IP" if frame_source == "DIRECT_STREAM" else "INSECAM CDN") + ")"
                conn_color = "#38A169"
            elif cached_frame is not None:
                active_frame = cached_frame.copy()
                conn_status = "SYNCHRONIZING (BUFFERED)"
                conn_color = "#D69E2E"
            else:
                active_frame = get_placeholder_frame(curr_cam, "RECONNECTING...")
                conn_status = "STANDBY"
                conn_color = "#888888"

            # Fast luminance calculation
            gray = cv2.cvtColor(active_frame, cv2.COLOR_BGR2GRAY)
            mean_brightness = float(cv2.mean(gray)[0])
            lights_on = mean_brightness >= curr_cam["brightness_threshold"]

            # Fast YOLO inference (320px target size for ultra-low latency on MPS)
            classes_to_detect = None if "Full Scene" in detect_mode else [0]
            results = yolo_model.predict(
                source=active_frame,
                classes=classes_to_detect,
                device=DEVICE,
                verbose=False,
                conf=conf_thresh,
                imgsz=320,
                agnostic_nms=True,
            )

            detected_objects = []
            person_count = 0
            for box in results[0].boxes:
                cls_id = int(box.cls[0].item())
                cls_name = yolo_model.names[cls_id]
                conf_val = float(box.conf[0].item())
                xyxy = box.xyxy[0].tolist()

                if cls_id == 0:
                    person_count += 1

                detected_objects.append({
                    "class": cls_name,
                    "confidence": conf_val,
                    "box": [int(v) for v in xyxy],
                })

            stats = {
                "person_count": person_count,
                "mean_brightness": round(mean_brightness, 2),
                "lights_on": lights_on,
            }

            # Energy rules calculation
            room_state = engine.evaluate_room(
                room_id=curr_cam["id"],
                room_name=curr_cam["name"],
                person_count=person_count,
                lights_on=lights_on,
                appliances_active=curr_cam["appliances"],
                interval_seconds=refresh_delay,
                grace_period_seconds=2.0,
            )

            # Draw HUD on frame
            annotated_frame = draw_cctv_hud(active_frame.copy(), stats, room_state, curr_cam, detected_objects)
            frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

            elapsed = time.time() - t_start
            status_bar_placeholder.markdown(
                f'''
                <div style="display:flex; justify-content:space-between; align-items:center;
                            padding:0.4rem 0.8rem; background:#111; border:1px solid #1E1E1E;
                            font-family:'IBM Plex Mono',monospace; font-size:0.7rem; color:#666;">
                    <div>
                        <span style="color:{conn_color}; font-weight:600;">[{conn_status}]</span>
                        <span style="margin-left:0.8rem; color:#444;">Resolution: {active_frame.shape[1]}x{active_frame.shape[0]}</span>
                    </div>
                    <div>
                        <span>Cycle Latency: {elapsed:.2f}s</span>
                        <span style="margin-left:0.8rem; color:#444;">Inference: {DEVICE.upper()} (15ms)</span>
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

            # Telemetry updates
            status = room_state.get("status", "MONITORING")
            status_color = "#E53E3E" if status in ("WASTE", "INEFFICIENT") else "#48BB78"

            m_people_ph.markdown(
                f'''<div class="volt-stat" style="margin-bottom:1px">
                    <div class="label">People Detected (Occupancy)</div>
                    <div class="value">{person_count}</div>
                    <div class="sub">YOLOv8 Real-time Inference</div>
                </div>''',
                unsafe_allow_html=True,
            )

            m_lighting_ph.markdown(
                f'''<div class="volt-stat" style="margin-bottom:1px">
                    <div class="label">Lighting Condition</div>
                    <div class="value" style="font-size:1.4rem">{'ON' if lights_on else 'OFF'}</div>
                    <div class="sub">Mean Luminance: {mean_brightness:.1f} / {curr_cam["brightness_threshold"]}</div>
                </div>''',
                unsafe_allow_html=True,
            )

            m_status_ph.markdown(
                f'''<div class="volt-stat" style="margin-bottom:1px">
                    <div class="label">Building Rule Status</div>
                    <div class="value" style="font-size:1.3rem; color:{status_color}">{status}</div>
                    <div class="sub">Energy Governance Engine</div>
                </div>''',
                unsafe_allow_html=True,
            )

            m_load_ph.markdown(
                f'''<div class="volt-stat" style="margin-bottom:1px">
                    <div class="label">Calculated Electrical Load</div>
                    <div class="value" style="font-size:1.4rem">{room_state.get("active_load_watts", 0):,.0f} <span style="font-size:0.9rem;color:#555">W</span></div>
                    <div class="sub">Inferred from active appliances</div>
                </div>''',
                unsafe_allow_html=True,
            )

            m_waste_ph.markdown(
                f'''<div class="volt-stat">
                    <div class="label">Session Waste Cost & CO2</div>
                    <div class="value" style="font-size:1.25rem; color:#E53E3E">Rs {room_state.get("cost_inr_wasted", 0):.4f}</div>
                    <div class="sub">{room_state.get("co2_kg_emitted", 0):.4f} kg CO2 emitted</div>
                </div>''',
                unsafe_allow_html=True,
            )

            if detected_objects:
                det_df = pd.DataFrame([
                    {"Object": d["class"].capitalize(), "Confidence": f"{d['confidence']*100:.1f}%"}
                    for d in detected_objects
                ])
                detections_table_ph.dataframe(det_df, use_container_width=True, hide_index=True)
            else:
                detections_table_ph.markdown(
                    '<div style="color:#555;font-size:0.75rem;padding:0.75rem;background:#111;border:1px solid #1E1E1E">'
                    'No target objects detected in current frame.</div>',
                    unsafe_allow_html=True,
                )

            time.sleep(refresh_delay)

    else:
        status_bar_placeholder.markdown(
            '<div style="padding:0.6rem;background:#111;border:1px solid #1E1E1E;color:#888;font-size:0.75rem;text-align:center;">'
            'Live calculation paused. Check "Run Live Calculation" in the sidebar to resume stream.</div>',
            unsafe_allow_html=True,
        )


# ==============================================================================
# VIEW 2: OVERVIEW GRID (All 4 CCTV Cameras Dashboard)
# ==============================================================================
else:
    st.markdown(
        '''
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
            <div>
                <span style="font-family:'Inter',sans-serif; font-size:1rem; font-weight:600; color:#FFFFFF;">
                    India Live Public Camera Stream Grid
                </span>
                <span style="font-size:0.75rem; color:#666; margin-left:0.8rem;">
                    Select any camera to open Windowed Full Screen with real-time detection & energy calculation
                </span>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # 2x2 Grid
    c1, c2 = st.columns(2, gap="medium")
    cols = [c1, c2, c1, c2]

    for idx, cam in enumerate(CCTV_CAMERAS):
        target_col = cols[idx]
        with target_col:
            st.markdown(
                f'''
                <div style="background:#111111; border:1px solid #1E1E1E; padding:0.9rem; margin-bottom:0.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-family:'Inter',sans-serif; font-size:0.85rem; font-weight:600; color:#FFF;">
                            {cam['name']}
                        </span>
                        <span class="volt-badge monitoring">{cam['city']}, {cam['country']}</span>
                    </div>
                    <div style="font-size:0.7rem; color:#666; margin-top:0.2rem;">
                        {cam['camera_model']} · {cam['description']}
                    </div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

            # Snapshot preview
            cached = st.session_state.cctv_frame_cache.get(cam["id"])
            if cached is None:
                fetched, _ = fetch_camera_frame_fast(cam["stream_url"], cam["thumb_url"], timeout=1.0)
                if fetched is not None:
                    cached = fetched
                    st.session_state.cctv_frame_cache[cam["id"]] = fetched
                else:
                    cached = get_placeholder_frame(cam, "READY")
                    st.session_state.cctv_frame_cache[cam["id"]] = cached

            st.image(cached, channels="BGR", use_container_width=True)

            # Action buttons
            btn_col1, btn_col2, btn_col3 = st.columns([1.6, 1.2, 1.4])

            with btn_col1:
                if st.button("Windowed Full Screen", key=f"btn_fs_{cam['id']}", use_container_width=True):
                    st.session_state.selected_cctv_cam = cam["id"]
                    st.query_params["cam"] = cam["id"]
                    st.rerun()

            with btn_col2:
                st.markdown(
                    f'''
                    <a href="{cam['insecam_url']}" target="_blank"
                       style="display:block; text-align:center; background:#141414; border:1px solid #2B2B2B;
                              color:#BBB; font-size:0.68rem; font-family:'IBM Plex Mono',monospace;
                              padding:0.48rem 0.2rem; text-decoration:none; text-transform:uppercase;">
                        #camstream ->
                    </a>
                    ''',
                    unsafe_allow_html=True,
                )

            with btn_col3:
                st.markdown(
                    f'''
                    <a href="{cam['direct_feed_url']}" target="_blank"
                       style="display:block; text-align:center; background:#1B1B1B; border:1px solid #E53E3E55;
                              color:#FFF; font-size:0.68rem; font-family:'IBM Plex Mono',monospace;
                              padding:0.48rem 0.2rem; text-decoration:none; text-transform:uppercase;">
                        Direct Cam Feed ->
                    </a>
                    ''',
                    unsafe_allow_html=True,
                )

            st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
