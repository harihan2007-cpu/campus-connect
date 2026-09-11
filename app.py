import os
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
from google import genai
from chatbot_config import CHATBOT_TITLE, CHATBOT_PURPOSE, SYSTEM_PROMPT, MAX_HISTORY_MESSAGES

load_dotenv()

MODEL_NAME = "gemini-3.1-flash-lite"

app = Flask(__name__)

api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None


@app.get("/")
def index():
    return render_template("index.html", chatbot_title=CHATBOT_TITLE, chatbot_purpose=CHATBOT_PURPOSE)


@app.post("/api/chat")
def chat():
    if not request.is_json:
        return jsonify({"error": "The request must contain JSON data."}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Invalid request data."}), 400

    message = data.get("message")
    history = data.get("history", [])

    if not isinstance(message, str) or not message.strip():
        return jsonify({"error": "Please enter a message."}), 400

    if not isinstance(history, list):
        history = []

    cleaned_history = []
    for item in history[-MAX_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role not in {"user", "assistant"}:
            continue
        if not isinstance(content, str) or not content.strip():
            continue
        cleaned_history.append({"role": role, "content": content.strip()[:4000]})

    if client is None:
        return jsonify({"error": "The chatbot is not configured right now."}), 503

    conversation = []
    for item in cleaned_history:
        speaker = "User" if item["role"] == "user" else "Assistant"
        conversation.append(f"{speaker}: {item['content']}")
    conversation.append(f"User: {message.strip()[:4000]}")

    prompt = SYSTEM_PROMPT + "\n\nConversation:\n" + "\n".join(conversation)

    try:
        response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
        reply = getattr(response, "text", None)
        if not isinstance(reply, str) or not reply.strip():
            return jsonify({"error": "The chatbot could not process your request right now."}), 502
        return jsonify({"reply": reply.strip()})
    except Exception:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "The chatbot could not process your request right now."}), 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
