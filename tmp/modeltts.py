from dotenv import load_dotenv
import os
from google import genai

load_dotenv()

key = os.getenv("GEMINI_API_KEY")

if not key:
    raise RuntimeError("gemini api key not found")

client = genai.Client(api_key=key)

for model in [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]:
    try:
        response = client.models.generate_content(
            model=model,
            contents="say hi"
        )
        print(f"{model}: {response.text}")
    except Exception as e:
        print(f"{model}: failed — {e}")