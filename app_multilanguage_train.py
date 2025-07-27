import random
import requests
from ruamel.yaml import YAML
import os
from pathlib import Path
import csv
import time

OLLAMA_URL = "http://localhost:11434/api/generate"
RASA_URL = "http://localhost:5005/webhooks/rest/webhook"
MODEL = "llama3"

LANGUAGES = ["Chinese", "Japanese", "French", "Spanish"]
INTENT_NAME = "query_knowledge_base"

NLU_FILE = "data/nlu.yml"
RESPONSES_FILE = "domain.yml"

TOPIC_LIST = [
    "how to connect a projector",
    "how to Operating the projector",
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

yaml = YAML()
yaml.preserve_quotes = True


def ask_ollama(prompt):
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        })
        res.raise_for_status()
        return res.json()["response"].strip()
    except requests.exceptions.RequestException as e:
        print(f"Error: Connection to Ollama failed: {e}")
        return ""
    except KeyError:
        print(f"Error: 'response' key not found in Ollama's output. Full response: {res.text}")
        return ""
    except Exception as e:
        print(f"An unexpected error occurred in ask_ollama: {e}")
        return ""


def generate_questions(topic, num_questions=5):
    lang = random.choice(LANGUAGES)
    prompt = f"Generate {num_questions} different ways a user might ask the question: '{topic}' and answer me in {lang}"
    raw = ask_ollama(prompt)
    if not raw:
        return []
    return [line.strip("-•0123456789. ").strip()
            for line in raw.split("\n") if line.strip()]


def generate_answer(question, lang):
    prompt = f"Answer the question below in BOTH English and {lang}:\n\n{question}"
    return ask_ollama(prompt)


def send_to_rasa(question):
    try:
        res = requests.post(RASA_URL, json={"sender": "test_user", "message": question})
        res.raise_for_status()
        responses = res.json()
        return " ".join([r.get("text", "") for r in responses if "text" in r])
    except requests.exceptions.RequestException as e:
        print(f"Error: Connection to Rasa failed: {e}")
        return ""


def append_to_nlu(intent_name, examples):
    if not examples:
        print("No examples to add to NLU.")
        return

    nlu_path = Path(NLU_FILE)
    nlu_path.parent.mkdir(parents=True, exist_ok=True)

    if not nlu_path.exists():
        nlu_data = {"version": "3.1", "nlu": []}
    else:
        with open(nlu_path, "r", encoding="utf-8") as f:
            try:
                nlu_data = yaml.load(f)
            except Exception as e:
                print(f"Error loading {NLU_FILE}: {e}")
                return

    if "nlu" not in nlu_data or nlu_data["nlu"] is None:
        nlu_data["nlu"] = []

    intent_entry = next((entry for entry in nlu_data["nlu"] if entry.get("intent") == intent_name), None)

    if intent_entry is None:
        intent_entry = {"intent": intent_name, "examples": ""}
        nlu_data["nlu"].append(intent_entry)

    existing_examples = intent_entry.get("examples", "")
    if not isinstance(existing_examples, str):
        existing_examples = ""

    example_set = set(e.strip() for e in existing_examples.split('\n- ') if e.strip())
    for example in examples:
        if example not in example_set:
            existing_examples += f"\n- {example}"
            example_set.add(example)

    intent_entry["examples"] = existing_examples.strip()
    if not intent_entry["examples"].startswith("- "):
        intent_entry["examples"] = "- " + intent_entry["examples"]

    with open(nlu_path, "w", encoding="utf-8") as f:
        yaml.dump(nlu_data, f)


def append_to_responses(intent_name, answers):
    if not answers:
        print("No answers to add to responses.")
        return

    responses_path = Path(RESPONSES_FILE)
    responses_path.parent.mkdir(parents=True, exist_ok=True)

    if not responses_path.exists():
        domain_data = {}
    else:
        with open(responses_path, "r", encoding="utf-8") as f:
            try:
                domain_data = yaml.load(f)
            except Exception as e:
                print(f"Error loading {RESPONSES_FILE}: {e}")
                return

    key = f"utter_{intent_name}"
    responses = domain_data.setdefault("responses", {}).setdefault(key, [])

    for answer in answers:
        if answer and {"text": answer} not in responses:
            responses.append({"text": answer})

    with open(responses_path, "w", encoding="utf-8") as f:
        yaml.dump(domain_data, f)


def log_to_csv(log_file, rows):
    with open(log_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def main():
    log_file = "rasa_generated_training_log.csv"
    with open(log_file, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Topic", "Generated Question", "Rasa Answer", "Multilingual Answer"])

    for topic in TOPIC_LIST:
        selected_lang = random.choice(LANGUAGES)
        print(f"\n📌 Topic: {topic} | Language: {selected_lang}")

        questions = generate_questions(topic)
        if not questions:
            print("Could not generate questions. Skipping topic.")
            continue

        csv_rows = []
        multilingual_answers = []

        for q in questions:
            print(f"❓ Q: {q}")
            rasa_answer = send_to_rasa(q)
            print(f"💬 Rasa A: {rasa_answer}")

            multilingual_answer = generate_answer(q, selected_lang)
            print(f"🌍 LLM A: {multilingual_answer}")

            csv_rows.append([topic, q, rasa_answer, multilingual_answer])
            if multilingual_answer:
                multilingual_answers.append(multilingual_answer)

            time.sleep(1)

        log_to_csv(log_file, csv_rows)
        append_to_nlu(INTENT_NAME, questions)
        append_to_responses(INTENT_NAME, multilingual_answers)
        print(f"\n✅ Successfully updated {NLU_FILE}, {RESPONSES_FILE}, and logged to {log_file}.")


if __name__ == "__main__":
    main()