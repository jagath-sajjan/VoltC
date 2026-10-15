import os
from dotenv import load_dotenv
from google import genai
from groq import Groq

load_dotenv()

def generate_action_plan(state_data: dict) -> str:
    if not state_data:
        return "No active building telemetry to analyze. Please run the live detection first."

    total_waste_inr = sum(r.get("cost_inr_wasted", 0) for r in state_data.values())
    total_co2 = sum(r.get("co2_kg_emitted", 0) for r in state_data.values())
    waste_rooms = [r["room_name"] for r in state_data.values() if r["status"] in ["WASTE", "INEFFICIENT"]]
    
    prompt = f"""
    You are an energy efficiency AI for the Nachos HQ Digital Twin.
    
    Current Live Telemetry:
    - Total wasted cost (current session): Rs {total_waste_inr:.4f}
    - Total CO2 emissions from inefficient rooms: {total_co2:.5f} kg
    - Rooms currently in WASTE or INEFFICIENT state: {', '.join(waste_rooms) if waste_rooms else 'None'}
    
    Provide a concise, 3-bullet action plan for the facility manager to mitigate this waste. 
    Briefly reference the high BESCOM commercial tariffs and the sustainability impact. 
    Keep it punchy, professional, and strictly under 100 words.
    """
    
    key = os.getenv("GEMINI_API_KEY")
    response_text = None
    last_gemini_error = None
    
    if key:
        try:
            client = genai.Client(api_key=key)
            models_to_try = [
                "gemini-3.8-flash",
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-pro"
            ]
            
            for model in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=prompt
                    )
                    if response and response.text:
                        response_text = response.text
                        break
                except Exception as model_err:
                    last_gemini_error = model_err
                    continue
        except Exception as client_err:
            last_gemini_error = client_err
            
    # If all Gemini models failed or key was missing, fall back to Groq
    if not response_text:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            try:
                groq_client = Groq(api_key=groq_key)
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": "You are an energy efficiency AI."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                response_text = completion.choices[0].message.content
            except Exception as groq_err:
                return f"**API Error:** All Gemini models and Groq fallback failed.\n\nGemini Error: {str(last_gemini_error)}\nGroq Error: {str(groq_err)}"
        else:
            return f"**API Error:** Gemini models failed and `GROQ_API_KEY` is not set.\n\nDetails: {str(last_gemini_error)}"
            
    return response_text