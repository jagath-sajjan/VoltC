import json
from pathlib import Path
import plotly.graph_objects as go

def load_data():
    """Loads static room data and dynamic state data."""
    with open("data/rooms.json", "r") as f:
        rooms_data = json.load(f)
    
    state_data = {}
    if Path("data/state.json").exists():
        with open("data/state.json", "r") as f:
            state_data = json.load(f)
            
    return rooms_data, state_data

def create_floor_plan(floor_num: int):
    """Draws a 2D Plotly map for a specific floor."""
    rooms_data, state_data = load_data()
    fig = go.Figure()
    
    # Status to color mapping
    color_map = {
        "EFFICIENT": "lightgray",
        "OCCUPIED": "lightgreen",
        "MONITORING": "khaki",
        "WASTE": "salmon",
        "UNKNOWN": "white"
    }

    # Draw each room on the selected floor
    for room in rooms_data["rooms"]:
        if room["floor"] != floor_num:
            continue
            
        r_id = room["id"]
        status = state_data.get(r_id, {}).get("status", "UNKNOWN")
        fill_color = color_map.get(status, "white")
        
        # Close the polygon by repeating the first coordinate at the end
        x_coords = room["coordinates"]["x"] + [room["coordinates"]["x"][0]]
        y_coords = room["coordinates"]["y"] + [room["coordinates"]["y"][0]]
        
        # Calculate center for text placement
        center_x = sum(x_coords[:-1]) / 4
        center_y = sum(y_coords[:-1]) / 4

        fig.add_trace(go.Scatter(
            x=x_coords,
            y=y_coords,
            fill="toself",
            fillcolor=fill_color,
            line=dict(color="black", width=2),
            mode="lines",
            name=room["name"],
            hoverinfo="skip"
        ))

        # Add labels in the center of the room
        fig.add_annotation(
            x=center_x,
            y=center_y,
            text=f"<b>{room['name']}</b><br>{status}",
            showarrow=False,
            font=dict(size=12, color="black")
        )

    # Clean up the axis so it looks like a blueprint
    fig.update_layout(
        title=f"Live Digital Twin: Floor {floor_num}",
        xaxis=dict(visible=False, range=[-1, 13]),
        yaxis=dict(visible=False, range=[-1, 10]),
        showlegend=False,
        height=500,
        margin=dict(l=0, r=0, t=40, b=0),
        plot_bgcolor="white"
    )
    return fig

if __name__ == "__main__":
    # Test script to generate HTML file to verify drawing
    fig = create_floor_plan(1)
    fig.write_html("test_map.html")
    print("[*] Map exported to test_map.html")