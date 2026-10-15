import json
from rules import EnergyRulesEngine

def initialize_building_state():
    """Resets the entire building to a baseline EFFICIENT state."""
    with open("data/rooms.json", "r") as f:
        rooms = json.load(f)["rooms"]
    
    engine = EnergyRulesEngine()
    state_cache = {}
    
    for room in rooms:
        # Default baseline: Room is empty, lights are off
        state_cache[room["id"]] = {
            "room_id": room["id"],
            "room_name": room["name"],
            "status": "EFFICIENT",
            "person_count": 0,
            "lights_on": False,
            "active_load_watts": engine.get_room_base_load(room["appliances"]),
            "waste_duration_seconds": 0.0,
            "kwh_wasted": 0.0,
            "cost_inr_wasted": 0.0,
            "co2_kg_emitted": 0.0
        }
        
    engine.save_state(state_cache)
    print(f"[*] Successfully initialized {len(rooms)} rooms to baseline EFFICIENT state.")

if __name__ == "__main__":
    initialize_building_state()