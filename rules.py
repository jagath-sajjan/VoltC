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
        
        # In-memory tracking per room
        self.room_tracker = {}

    def get_room_base_load(self, room_appliances: list[str]) -> float:
        """Returns total wattage for a list of appliance names."""
        return sum(self.appliances.get(app, 0) for app in room_appliances)

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
        """
        Evaluates energy state for a single room observation interval.
        - interval_seconds: time step between evaluation frames (e.g. 0.4s)
        - grace_period_seconds: threshold before flagging waste
        """
        if room_id not in self.room_tracker:
            self.room_tracker[room_id] = {
                "consecutive_empty_lit_seconds": 0.0,
                "total_waste_seconds": 0.0
            }

        tracker = self.room_tracker[room_id]
        total_watts = self.get_room_base_load(appliances_active)

        # Waste Condition: Lights are on, but nobody is inside
        is_empty_lit = lights_on and (person_count == 0)

        if is_empty_lit:
            tracker["consecutive_empty_lit_seconds"] += interval_seconds
        else:
            tracker["consecutive_empty_lit_seconds"] = 0.0

        # State determination
        if tracker["consecutive_empty_lit_seconds"] >= grace_period_seconds:
            status = "WASTE"
            tracker["total_waste_seconds"] += interval_seconds
        elif person_count > 0:
            status = "OCCUPIED"
        elif lights_on:
            status = "MONITORING"
        else:
            status = "EFFICIENT"

        # Math: kWh, INR, CO2
        waste_hours = tracker["total_waste_seconds"] / 3600.0
        kwh_wasted = (total_watts * waste_hours) / 1000.0
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
        """Dumps latest digital twin room state to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(rooms_state, f, indent=2)


if __name__ == "__main__":
    # Test stub verifying math logic
    engine = EnergyRulesEngine()
    
    # Test a room with 2 tube lights and 1 AC
    apps = ["tube_light", "tube_light", "ac_1_5_ton"]
    
    print("[*] Testing Rules Engine simulation:")
    # Simulate 5 ticks of empty lit room (0.8s each = 4.0s total)
    for tick in range(1, 6):
        res = engine.evaluate_room(
            room_id="room_101",
            room_name="Lab 101",
            person_count=0,
            lights_on=True,
            appliances_active=apps,
            interval_seconds=0.8,
            grace_period_seconds=2.0
        )
        print(f"Tick {tick}: Status={res['status']} | Waste={res['waste_duration_seconds']}s | ₹={res['cost_inr_wasted']}")

    engine.save_state({"room_101": res})
    print(f"[*] State exported cleanly to {STATE_PATH}")