from flask import Flask, render_template, request
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

# Setup Hugging Face client
HF_TOKEN = os.getenv("HF_TOKEN")
client = InferenceClient(token=HF_TOKEN)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    feeling = request.form.get("feeling")
    goal = request.form.get("goal")

    # Prompt for the AI
    prompt = f"Give a motivating message to help achieve goal: {goal} considering that they feel: {feeling}."

    # Generate from Hugging Face model
    try:
        response = client.chat_completion(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}]

        )
        
        # Extract the AI message
        message = response['choices'][0]['message']['content'].strip()

    except Exception as e:
        import traceback
        traceback.print_exc()
        message = f"Error generating message: {e}"
    
    return render_template("result.html", message=message)

if __name__ == "__main__":
    app.run(debug=True)