import os
import time
from mistralai import Mistral
from dotenv import load_dotenv
load_dotenv()


# ── Config 

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MODEL_NAME      = "ministral-8b-2512"

MAX_RETRIES = 2
RETRY_DELAY = 1  # seconds


# ── Client Init 

if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY not set")

client = Mistral(api_key=MISTRAL_API_KEY)


# ── Core LLM Call ────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> str:
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.chat.complete(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.2,
                max_tokens=500,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
            else:
                return f"[LLM ERROR] {str(e)}"