from huggingface_hub import InferenceClient, HfApi
from dotenv import load_dotenv
import os
import sys

# Load .env and override any system/global variables
load_dotenv(override=True)

# Get token directly from env
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    print("No HF_TOKEN found in .env or environment variables.")
    sys.exit(1)

print("Using HF_TOKEN from .env")

# Test the token before continuing
try:
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Token valid for user: {whoami['name']}")
except Exception as e:
    print("Invalid token:", e)
    sys.exit(1)

# Initialize client with the good token
client = InferenceClient(token=HF_TOKEN)

prompt = "Give me a short motivational quote:"

# Some models may not support chat_completion.
# If chat_completion fails, fall back to text_generation.
try:
    response = client.chat_completion(
        model="openai/gpt-oss-20b",
        messages=[{"role": "user", "content": prompt}]
    )
    print("Response:", response['choices'][0]['message']['content'])
except Exception as e:
    print("chat_completion failed, trying text_generation...", e)
    response = client.text_generation(
        model="openai/gpt-oss-20b",
        inputs=prompt,
        max_new_tokens=50
    )
    print("Response:", response.generated_text)
