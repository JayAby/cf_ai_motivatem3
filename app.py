from flask import Flask, render_template, request
from huggingface_hub import InferenceClient
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util 
from dotenv import load_dotenv
from requests.exceptions import ContentDecodingError
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

# Emotion Classifier
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)

def detect_emotion(user_text):
    results = emotion_classifier(user_text)[0] # Returns list of emotions
    top_emotion = max(results, key=lambda x: x['score'])
    return top_emotion['label'], top_emotion['score']

def map_emotion_to_mood(emotion):
    mapping = {
    "joy": "joy",
    "anger": "anger",
    "sadness": "sadness",
    "fear": "fear",
    "surprise": "surprise",
    "love": "love",
    "neutral": "neutral",
    "disgust": "disgust"
    }
    return mapping.get(emotion.lower(), "neutral")

# Detect harmful intent
semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
negative_intents = [
    "steal", "rob", "kill", "hurt someone", "suicide", "crime", "mafia", "illegal",
    "attack", "harm", "fraud", "worthless", "give up", "sexual desire"
]
neg_embs = semantic_model.encode(negative_intents, convert_to_tensor=True)

def is_harmful(user_text):
    user_emb = semantic_model.encode(user_text, convert_to_tensor=True)
    scores = util.cos_sim(user_emb, neg_embs)[0] # Compare user text to negative intents
    return any(score > 0.65 for score in scores)

# Create Motivational Prompt
def reframe_input(feeling, goal):
    # Detect emotion
    emotion, _ = detect_emotion(feeling or goal)
    combined_text = f"{feeling}. Goal: {goal}"

    # Check user feeling
    if is_harmful(combined_text) or emotion.lower() in ["anger", "fear", "sadness"]:
        safe_reframed_prompt = (
            "The user has expressed risky, illegal, or sexual thoughts. " \
            "Rephrase their thoughts in a neutral, safe way, " \
            "so that it can be used to give positive motivational advice. " \
            f"The user input: {combined_text}."
        )

        try:
            # Generate safe text from AI
            response = client.chat_completion(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": safe_reframed_prompt}]
            )
            safe_text = response['choices'][0]['message']['content'].strip()

        except Exception as e:
            print("Error in safe reframing:", e)
            safe_text = combined_text
                
        # Final motivational prompt
        reframed_prompt = (
            f"Provide uplifting, safe, motivational advice based on this rephrased input: '{safe_text}'."
        )
    
    else:
        reframed_prompt = (
            f"Give a motivating message to help achieve goal: '{goal}' "
            f"while considering they feel: {feeling}."
        )

    return reframed_prompt


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    feeling = request.form.get("feeling", "").strip()
    goal = request.form.get("goal", "").strip()

    if not goal and not feeling:
        return render_template("result.html", message="Please provide a goal or a feeling.")
    
    # Detect emotion and map to mood
    text_to_analyze = feeling or goal
    emotion, _ = detect_emotion(text_to_analyze)
    detected_mood = map_emotion_to_mood(emotion)

    # Use reframe input as prompt
    prompt = reframe_input(feeling, goal)

    # Generate from Hugging Face model
    try:
        response = client.chat_completion(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}]

        )  
        # Extract the AI message
        raw_message = response['choices'][0]['message']['content'].strip()

    except Exception as e:
        print(f"Error with chat_completion: {e}")
        try:
            # Fallback: use text_generation if chat_completion is not supported
            response = client.text_generation(
                model="openai/gpt-oss-20b",
                prompt=prompt,
                max_new_tokens=100
            )
            raw_message = response.generated_text.strip()

        except Exception as e:
            print(f"Error with text_generation fallback: {e}")
            raw_message = "Sorry, there was an error generating motivation."

    # Render with Markdown
    message = markdown.markdown(raw_message, extensions=["tables", "fenced_code"])

    
    return render_template("result.html", message=message, mood=detected_mood.lower())

if __name__ == "__main__":
    app.run(debug=True)