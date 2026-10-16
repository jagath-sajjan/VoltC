import json
from pathlib import Path
import plotly.graph_objects as go


def load_data():
    with open("data/rooms.json", "r") as f:
        rooms_data = json.load(f)

    state_data = {}
    if Path("data/state.json").exists():
        with open("data/state.json", "r") as f:
            state_data = json.load(f)

    return rooms_data, state_data


# Status colour mapping — original readable palette kept intact
_STATUS_FILL = {
    "WASTE":       "salmon",
    "INEFFICIENT": "orange",
    "OCCUPIED":    "lightgreen",
    "MONITORING":  "khaki",
    "EFFICIENT":   "lightgray",
    "UNKNOWN":     "#2A2A2A",
}

_STATUS_BORDER = {
    "WASTE":       "#cc3333",
    "INEFFICIENT": "#cc7700",
    "OCCUPIED":    "#33aa33",
    "MONITORING":  "#999900",
    "EFFICIENT":   "#666666",
    "UNKNOWN":     "#333333",
}

_STATUS_TEXT = {
    "WASTE":       "#8B0000",
    "INEFFICIENT": "#7A3B00",
    "OCCUPIED":    "#1a5c1a",
    "MONITORING":  "#5c5c00",
    "EFFICIENT":   "#444444",
    "UNKNOWN":     "#888888",
}


def create_floor_plan(floor_num: int):
    rooms_data, state_data = load_data()
    fig = go.Figure()

    for room in rooms_data["rooms"]:
        if room["floor"] != floor_num:
            continue

        r_id   = room["id"]
        status = state_data.get(r_id, {}).get("status", "EFFICIENT")
        load_w = state_data.get(r_id, {}).get("active_load_watts", 0)

        fill_color   = _STATUS_FILL.get(status, "#FFFFFF04")
        border_color = _STATUS_BORDER.get(status, "#222222")
        text_color   = _STATUS_TEXT.get(status, "#555555")

        x_coords = room["coordinates"]["x"] + [room["coordinates"]["x"][0]]
        y_coords = room["coordinates"]["y"] + [room["coordinates"]["y"][0]]

        center_x = sum(room["coordinates"]["x"]) / 4
        center_y = sum(room["coordinates"]["y"]) / 4

        # Room shape
        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color=border_color, width=1),
            mode="lines",
            name=room["name"],
            hoverinfo="skip",
            showlegend=False,
        ))

        # Room name annotation
        short_name = room["name"].split("&")[0].strip()
        if len(short_name) > 18:
            short_name = short_name[:16] + "…"

        # Room name — dark text on light bg
        fig.add_annotation(
            x=center_x,
            y=center_y + 0.35,
            text=f"<span style='font-family:Inter;font-size:10px;color:#1A1A1A'>{short_name}</span>",
            showarrow=False,
            font=dict(size=10, color="#1A1A1A"),
        )

        # Status + load — slightly muted dark text
        load_str = f"{load_w:,}W" if load_w else ""
        status_text_color = _STATUS_TEXT.get(status, "#333333")
        fig.add_annotation(
            x=center_x,
            y=center_y - 0.35,
            text=f"<span style='font-family:IBM Plex Mono,monospace;font-size:9px;color:{status_text_color}'>{status}  {load_str}</span>",
            showarrow=False,
            font=dict(size=9, color=status_text_color),
        )

    fig.update_layout(
        xaxis=dict(visible=False, range=[-0.5, 13]),
        yaxis=dict(visible=False, range=[-0.5, 9.5]),
        showlegend=False,
        height=340,
        margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="#F2F2F2",
        paper_bgcolor="#0A0A0A",
    )
    return fig


if __name__ == "__main__":
    fig = create_floor_plan(1)
    fig.write_html("test_map.html")
    print("[*] Map exported to test_map.html")