
from google import genai
import os

PROJECT_ID = "gen-lang-client-0380898052"
LOCATION = "global"
MODEL = "gemini-3.5-flash-lite"

client = genai.Client(
    vertexai=True,
    project=PROJECT_ID,
    location=LOCATION,
)

try:
    response = client.models.generate_content(
        model=MODEL,
        contents="Say hello to DailyPulse AI in one sentence."
    )

    print("\nSUCCESS! Vertex AI is working.")
    print(response.text)

except Exception as e:
    print("\nVERTEX AI TEST FAILED")
    print(type(e).__name__)
    print(str(e))

finally:
    client.close()
