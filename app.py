from flask import Flask, render_template, request
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os
import markdown

# Load .env and override any system/global variables
load_dotenv(override=True)

app = Flask(__name__)

# Get HF Token
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN is missing. Please add it to your .env file.")

# Setup Hugging Face client
client = InferenceClient(token=HF_TOKEN)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    feeling = request.form.get("feeling", "").strip()
    goal = request.form.get("goal", "").strip()

    if not goal and not feeling:
        return render_template("result.html", message="Please provide a goal or a feeling.")

    # Prompt for the AI
    prompt = f"Give a motivating message to help achieve goal: {goal} while considering they feel: {feeling}."

    # Generate from Hugging Face model
    try:
        response = client.chat_completion(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}]

        )
        
        # Extract the AI message
        raw_message = response['choices'][0]['message']['content'].strip()

    except Exception:
        # Fallback: use text_generation if chat_completion is not supported
        response = client.text_generation(
            model="openai/gpt-oss-20b",
            prompt=prompt,
            max_new_tokens=80
        )
        raw_message = response.generated_text.strip()

    # Render with Markdown
    message = markdown.markdown(raw_message, extensions=["tables", "fenced_code"])

    
    return render_template("result.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)