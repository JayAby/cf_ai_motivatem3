from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

# Initialize client
client = InferenceClient(token=HF_TOKEN)

prompt = "Give me a short motivational quote:"

# Use chat_completion for conversational models
response = client.chat_completion(
    model="openai/gpt-oss-20b",
    messages=[{"role": "user", "content": prompt}]
)

# Print the generated text
print(response['choices'][0]['message']['content'])
