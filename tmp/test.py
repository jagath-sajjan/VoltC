from google import genai

prompt="how to sustain electricities"

client = genai.Client()
r = client.models.generate_content(
    model = "gemini-3.8-flash",
    contents = prompt)
print(r.text)