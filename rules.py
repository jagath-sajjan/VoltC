import json
from pathlib import Path

CONFIG_PATH = Path("data/apconfig.json")
STATE_PATH = Path("data/state.json")

class EnergyRulesEngine:
    def __init__(self, config_path: Path = CONFIG_PATH):
        with open(config_path, "r") as f:
            self.config = json.load(f)
            
        self.tariff = self.config["rates"]["tariff_inr_per_kwh"]
        self.co2_factor = self.config["rates"]["emission_kg_co2_per_kwh"]
        self.appliances = self.config["appliances_watts"]
        
        self.infrastructure_appliances = ["server_rack"]
        
        self.room_tracker = {}

    def get_room_loads(self, room_appliances: list[str]) -> tuple[float, float]:
        total_watts = 0.0
        switchable_watts = 0.0
        
        for app in room_appliances:
            w = self.appliances.get(app, 0)
            total_watts += w
            if app not in self.infrastructure_appliances:
                switchable_watts += w
                
        return total_watts, switchable_watts

    def evaluate_room(
        self,
        room_id: str,
        room_name: str,
        person_count: int,
        lights_on: bool,
        appliances_active: list[str],
        interval_seconds: float,
        grace_period_seconds: float = 3.0
    ) -> dict:
        if room_id not in self.room_tracker:
            self.room_tracker[room_id] = {
                "consecutive_empty_lit_seconds": 0.0,
                "total_waste_seconds": 0.0
            }

        tracker = self.room_tracker[room_id]
        total_watts, switchable_watts = self.get_room_loads(appliances_active)

        is_empty_lit = lights_on and (person_count == 0)
        is_low_load = switchable_watts < 200.0  # Forgive rooms with minimal lighting like the outdoor deck

        if is_empty_lit and not is_low_load:
            tracker["consecutive_empty_lit_seconds"] += interval_seconds
        else:
            tracker["consecutive_empty_lit_seconds"] = 0.0

        # State determination
        if tracker["consecutive_empty_lit_seconds"] >= grace_period_seconds:
            status = "WASTE"
            tracker["total_waste_seconds"] += interval_seconds
        elif person_count > 0:
            if person_count == 1 and switchable_watts > 1000 and lights_on:
                status = "INEFFICIENT"
                tracker["total_waste_seconds"] += (interval_seconds * 0.8)
            else:
                status = "OCCUPIED"
        elif lights_on and not is_low_load:
            status = "MONITORING"
        else:
            status = "EFFICIENT"

        waste_hours = tracker["total_waste_seconds"] / 3600.0
        kwh_wasted = (switchable_watts * waste_hours) / 1000.0
        cost_inr = kwh_wasted * self.tariff
        co2_kg = kwh_wasted * self.co2_factor

        return {
            "room_id": room_id,
            "room_name": room_name,
            "status": status,
            "person_count": person_count,
            "lights_on": lights_on,
            "active_load_watts": total_watts,
            "waste_duration_seconds": round(tracker["total_waste_seconds"], 2),
            "kwh_wasted": round(kwh_wasted, 5),
            "cost_inr_wasted": round(cost_inr, 4),
            "co2_kg_emitted": round(co2_kg, 5)
        }

    def save_state(self, rooms_state: dict, output_path: Path = STATE_PATH):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(rooms_state, f, indent=2)