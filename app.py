import requests
import csv
import time
import random

OLLAMA_URL = "http://localhost:11434/api/generate"

RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
MODEL = "llama3"
TOPIC_LIST = [
    "how to connect a projector",
    "how to Operating the projector"
    "how to reset the device",
    "how to Managing the lamp",
    "how to Managing content,playlists, and storage",
    "how to check lamp hours",
    "how to Working with channels",
    "what is the current projector model",
    "how to Managing color setting files",
    "how to fix keystone issue",
    "how to work with Test patterns"
]

def generate_questions(topic, num_questions=5):
    langs = ["chinese", "japanese", "french", "spanish"]
    lang = random.choice(langs)
    prompt = f"Generate {num_questions} different ways a user might ask the question: '{topic}' and answer me in {lang}"
    res = requests.post(OLLAMA_URL, json={"model": MODEL, "prompt": prompt, "stream": False})
    raw = res.json()["response"]
    return [line.strip("-•0123456789. ").strip() for line in raw.strip().split("\n") if line.strip()]

def send_to_rasa(question):
    res = requests.post(RASA_URL, json={"sender": "test_user", "message": question})
    responses = res.json()
    return " ".join([r.get("text", "") for r in responses if "text" in r])

def log_to_csv(log_file, rows):
    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)

def main():
    log_file = "rasa_generated_training_log.csv"
    with open(log_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Topic", "Generated Question", "Rasa Answer"])

    for topic in TOPIC_LIST:
        print(f"\n📌 Topic: {topic}")
        questions = generate_questions(topic)
        rows = []

        for q in questions:
            print(f"❓ Q: {q}")
            try:
                answer = send_to_rasa(q)
                print(f"💬 A: {answer}")
                rows.append([topic, q, answer])
                time.sleep(1)  # avoid flooding server
            except Exception as e:
                print("❌ Error:", e)

        log_to_csv(log_file, rows)

if __name__ == "__main__":
    main()
