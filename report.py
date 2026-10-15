import os
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env
load_dotenv()

def generate_action_plan(state_data: dict) -> str:
    """Sends aggregated digital twin state to Gemini for recommendations."""
    if not state_data:
        return "No active building telemetry to analyze. Please run the live detection first."

    # Aggregate current metrics across the building
    total_waste_inr = sum(r.get("cost_inr_wasted", 0) for r in state_data.values())
    total_co2 = sum(r.get("co2_kg_emitted", 0) for r in state_data.values())
    waste_rooms = [r["room_name"] for r in state_data.values() if r["status"] == "WASTE"]
    
    prompt = f"""
    You are an energy efficiency AI for the Nachos HQ Digital Twin.
    
    Current Live Telemetry:
    - Total wasted cost (current session): ₹{total_waste_inr:.4f}
    - Total CO2 emissions from empty rooms: {total_co2:.5f} kg
    - Rooms currently in WASTE state (empty but lit): {', '.join(waste_rooms) if waste_rooms else 'None'}
    
    Provide a concise, 3-bullet action plan for the facility manager to mitigate this waste. 
    Briefly reference the high BESCOM commercial tariffs and the sustainability impact. 
    Keep it punchy, professional, and strictly under 100 words.
    """
    
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"**API Error:** Make sure `GEMINI_API_KEY` is set in your `.env` file.\n\nDetails: {str(e)}"