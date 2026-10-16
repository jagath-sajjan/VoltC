import streamlit as st
import cv2
import pandas as pd
import atexit
import signal
import threading
from datetime import datetime

from twin import create_floor_plan, load_data
from detector import RoomDetector
from rules import EnergyRulesEngine
from report import generate_action_plan
from sim import initialize_building_state
from overlay import draw_overlay
from styles import inject_styles

st.set_page_config(
    page_title="VoltC",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()


# ── SERVER LIFECYCLE ─────────────────────────────────────────────────────────
@st.cache_resource
def _register_server_lifecycle():
    initialize_building_state()

    def _on_server_stop():
        initialize_building_state()

    atexit.register(_on_server_stop)
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGTERM, lambda s, f: _on_server_stop())
        signal.signal(signal.SIGINT,  lambda s, f: _on_server_stop())
    return True


_register_server_lifecycle()
rooms_data, state_data = load_data()


# ── HELPERS ──────────────────────────────────────────────────────────────────
def _badge(status: str) -> str:
    cls = status.lower()
    return f'<span class="volt-badge {cls}">{status}</span>'


def _total_load(state: dict) -> float:
    return sum(r.get("active_load_watts", 0) for r in state.values())


def _waste_rooms(state: dict) -> list:
    return [r for r in state.values() if r.get("status") in ("WASTE", "INEFFICIENT")]


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
floors = sorted(set(r["floor"] for r in rooms_data["rooms"]))

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
    st.page_link("app.py",                   label="Overview")
    st.page_link("pages/Webcam_Feed.py",      label="Live Webcam")

    st.markdown('<div class="volt-section-header">Floor</div>', unsafe_allow_html=True)
    selected_floor = st.selectbox("Floor Level", floors, label_visibility="collapsed")

    floor_rooms = {r["name"]: r for r in rooms_data["rooms"] if r["floor"] == selected_floor}

    st.markdown('<div class="volt-section-header">Camera</div>', unsafe_allow_html=True)
    selected_room_name = st.selectbox("Room Camera", list(floor_rooms.keys()), label_visibility="collapsed")
    selected_room = floor_rooms[selected_room_name]

    start_feed = st.checkbox("Run live detection", value=True)


# ── TOPBAR ────────────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%d %b  %H:%M")
total_w = _total_load(state_data)
waste_list = _waste_rooms(state_data)
waste_cost = sum(r.get("cost_inr_wasted", 0) for r in waste_list)

st.markdown(
    f'''
    <div class="volt-topbar">
        <div>
            <span style="font-family:Inter;font-size:1.1rem;font-weight:600;
                         color:#fff;letter-spacing:-0.01em">Nachos HQ</span>
            <span style="font-family:Inter;font-size:0.75rem;color:#444;
                         margin-left:1rem">Block A · Floor {selected_floor}</span>
        </div>
    </div>
    ''',
    unsafe_allow_html=True,
)


# ── HEADLINE METRICS ──────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(
        f'''<div class="volt-stat">
            <div class="label">Total Load</div>
            <div class="value">{total_w:,.0f}<span style="font-size:1rem;color:#444"> W</span></div>
            <div class="sub">Across all monitored rooms</div>
        </div>''',
        unsafe_allow_html=True,
    )

with m2:
    st.markdown(
        f'''<div class="volt-stat">
            <div class="label">Wasteful Rooms</div>
            <div class="value" style="color:{'#E53E3E' if waste_list else '#555'}">{len(waste_list)}</div>
            <div class="sub">WASTE or INEFFICIENT status</div>
        </div>''',
        unsafe_allow_html=True,
    )

with m3:
    st.markdown(
        f'''<div class="volt-stat">
            <div class="label">Session Waste Cost</div>
            <div class="value" style="font-size:1.5rem">Rs {waste_cost:,.2f}</div>
            <div class="sub">BESCOM @ Rs 9.50 / kWh</div>
        </div>''',
        unsafe_allow_html=True,
    )

with m4:
    active_rooms = sum(1 for r in state_data.values() if r.get("person_count", 0) > 0)
    st.markdown(
        f'''<div class="volt-stat">
            <div class="label">Occupied Rooms</div>
            <div class="value">{active_rooms}</div>
            <div class="sub">People detected this session</div>
        </div>''',
        unsafe_allow_html=True,
    )

st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)


# ── MAIN CONTENT ──────────────────────────────────────────────────────────────
left_col, right_col = st.columns([2, 1.1], gap="large")

with left_col:
    st.markdown('<div class="volt-section-header">Floor Plan — Live Status</div>', unsafe_allow_html=True)
    map_placeholder = st.empty()
    map_placeholder.plotly_chart(
        create_floor_plan(selected_floor),
        use_container_width=True,
        key="initial_map",
    )

    # Room status table
    st.markdown('<div class="volt-section-header">Room Telemetry</div>', unsafe_allow_html=True)
    table_placeholder = st.empty()

    floor_room_ids = [r["id"] for r in rooms_data["rooms"] if r["floor"] == selected_floor]
    floor_state = [v for k, v in state_data.items() if k in floor_room_ids]

    if floor_state:
        import pandas as pd
        df = pd.DataFrame(floor_state)[[
            "room_name", "status", "person_count",
            "active_load_watts", "cost_inr_wasted", "co2_kg_emitted"
        ]].rename(columns={
            "room_name":          "Room",
            "status":             "Status",
            "person_count":       "People",
            "active_load_watts":  "Load (W)",
            "cost_inr_wasted":    "Waste (Rs)",
            "co2_kg_emitted":     "CO2 (kg)",
        })
        table_placeholder.dataframe(df, use_container_width=True, hide_index=True)
    else:
        table_placeholder.markdown(
            '<div style="color:#444;font-size:0.8rem;padding:1rem 0">'
            'No telemetry for this floor yet. Run detection.</div>',
            unsafe_allow_html=True,
        )


with right_col:
    st.markdown(
        f'<div class="volt-section-header">Camera — {selected_room_name}</div>',
        unsafe_allow_html=True,
    )
    video_placeholder   = st.empty()
    metrics_placeholder = st.empty()

    if not start_feed:
        video_placeholder.markdown(
            '<div style="border:1px solid #1E1E1E;padding:2rem;color:#444;font-size:0.8rem">'
            'Enable "Run live detection" in the sidebar to connect.</div>',
            unsafe_allow_html=True,
        )

    if start_feed:
        room_threshold = selected_room.get("brightness_threshold", 75.0)
        detector = RoomDetector(brightness_threshold=room_threshold)
        engine   = EnergyRulesEngine()

        cap = cv2.VideoCapture(selected_room["clip"])
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        sample_step      = 10
        interval_seconds = sample_step / fps
        frame_idx        = 0

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
                    grace_period_seconds=2.0,
                )

                state_data[selected_room["id"]] = room_state
                engine.save_state(state_data)

                frame = draw_overlay(frame, stats, room_state)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                video_placeholder.image(frame_rgb, channels="RGB", use_container_width=True)

                status      = room_state["status"]
                status_color = "#E53E3E" if status in ("WASTE", "INEFFICIENT") else "#555555"
                cost         = room_state["cost_inr_wasted"]

                metrics_placeholder.markdown(
                    f'''<div style="display:flex;gap:1.5rem;padding:0.75rem 0;
                                    border-top:1px solid #1E1E1E;margin-top:0.5rem">
                        <div>
                            <div style="font-size:0.6rem;text-transform:uppercase;
                                        letter-spacing:0.1em;color:#444">Status</div>
                            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;
                                        color:{status_color};margin-top:0.2rem">{status}</div>
                        </div>
                        <div>
                            <div style="font-size:0.6rem;text-transform:uppercase;
                                        letter-spacing:0.1em;color:#444">People</div>
                            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;
                                        color:#aaa;margin-top:0.2rem">{stats["person_count"]}</div>
                        </div>
                        <div>
                            <div style="font-size:0.6rem;text-transform:uppercase;
                                        letter-spacing:0.1em;color:#444">Waste Cost</div>
                            <div style="font-family:'IBM Plex Mono',monospace;font-size:0.85rem;
                                        color:#E53E3E;margin-top:0.2rem">Rs {cost:.4f}</div>
                        </div>
                    </div>''',
                    unsafe_allow_html=True,
                )

            frame_idx += 1

        cap.release()
        map_placeholder.plotly_chart(
            create_floor_plan(selected_floor),
            use_container_width=True,
            key="final_map",
        )

        floor_state = [v for k, v in state_data.items() if k in floor_room_ids]
        if floor_state:
            import pandas as pd
            df_final = pd.DataFrame(floor_state)[[
                "room_name", "status", "person_count",
                "active_load_watts", "cost_inr_wasted", "co2_kg_emitted"
            ]].rename(columns={
                "room_name":         "Room",
                "status":            "Status",
                "person_count":      "People",
                "active_load_watts": "Load (W)",
                "cost_inr_wasted":   "Waste (Rs)",
                "co2_kg_emitted":    "CO2 (kg)",
            })
            table_placeholder.dataframe(df_final, use_container_width=True, hide_index=True)


# ── ANALYTICS ─────────────────────────────────────────────────────────────────
st.markdown('<div class="volt-section-header" style="margin-top:2rem">Analytics</div>', unsafe_allow_html=True)

sim_col, ai_col = st.columns([1, 1], gap="large")

with sim_col:
    st.markdown(
        '<div style="font-size:0.8rem;color:#888;margin-bottom:0.25rem">What-If Simulator</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.72rem;color:#444;margin-bottom:0.75rem">'
        'Estimate monthly savings if motion-triggered auto-off sensors are installed.</div>',
        unsafe_allow_html=True,
    )

    daily_waste_hours = st.slider(
        "Daily waste per room (hours)",
        min_value=1, max_value=10, value=4,
    )
    active_rooms = max(len(state_data), 1)
    monthly_kwh  = active_rooms * 2.0 * daily_waste_hours * 22
    monthly_inr  = monthly_kwh * 9.50
    monthly_co2  = monthly_kwh * 0.71

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Monthly Savings", f"Rs {monthly_inr:,.0f}", f"{monthly_kwh:,.0f} kWh recovered")
    with c2:
        st.metric("CO2 Reduction", f"{monthly_co2:,.0f} kg", "avoided per month")

with ai_col:
    st.markdown(
        '<div style="font-size:0.8rem;color:#888;margin-bottom:0.25rem">Facility Report</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="font-size:0.72rem;color:#444;margin-bottom:0.75rem">'
        'AI-generated action plan based on current session telemetry.</div>',
        unsafe_allow_html=True,
    )

    if st.button("Generate Report"):
        with st.spinner("Querying model..."):
            report_text = generate_action_plan(state_data)
            st.markdown(
                '<div style="border-left:2px solid #E53E3E;padding-left:1rem;margin-top:1rem">',
                unsafe_allow_html=True,
            )
            st.markdown(report_text)
            st.markdown("</div>", unsafe_allow_html=True)