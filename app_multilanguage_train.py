import random
import requests
from ruamel.yaml import YAML
import os
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"  # Or your multilingual Ollama model

LANGUAGES = ["Chinese", "Japanese", "English", "French", "Spanish"]
INTENT_NAME = "ask_projector_setup"

NLU_FILE = "data/nlu.yml"
RESPONSES_FILE = "domain.yml"

yaml = YAML()
yaml.preserve_quotes = True


def ask_ollama(prompt):
    try:
        res = requests.post(OLLAMA_URL, json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False
        })
        res.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
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


def generate_questions(base_topic, num_questions=5):
    prompt = f"Generate {num_questions} natural ways someone might ask: '{base_topic}'"
    raw = ask_ollama(prompt)
    if not raw:
        return []
    return [line.strip("-•0123456789. ").strip()
            for line in raw.split("\n") if line.strip()]


def generate_answer(question, lang):
    prompt = f"Answer the question below in BOTH English and {lang}:\n\n{question}"
    return ask_ollama(prompt)


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

    # Find or create the intent entry
    intent_entry = None
    for entry in nlu_data["nlu"]:
        if entry.get("intent") == intent_name:
            intent_entry = entry
            break

    if intent_entry is None:
        intent_entry = {"intent": intent_name, "examples": ""}
        nlu_data["nlu"].append(intent_entry)

    # Ensure examples is a string and add new examples
    existing_examples = intent_entry.get("examples", "")
    if not isinstance(existing_examples, str):
        existing_examples = "" # Reset if it's not a string

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


def run_multilingual_training(topic, num_questions=5):
    selected_lang = random.choice(LANGUAGES)
    print(f"🗣️ Generating questions in English for topic: {topic}")
    print(f"🌍 Answering in: English + {selected_lang}\n")

    questions = generate_questions(topic, num_questions)
    if not questions:
        print("Could not generate questions. Aborting.")
        return

    answers = [generate_answer(q, selected_lang) for q in questions]
    answers = [a for a in answers if a] # Filter out empty answers

    if not answers:
        print("Could not generate any answers. Aborting.")
        return

    print("\n📦 Generated Training Data:\n")
    for q, a in zip(questions, answers):
        print(f"Q: {q}\nA: {a}\n{'-'*40}")

    # Append to NLU and Domain
    append_to_nlu(INTENT_NAME, questions)
    append_to_responses(INTENT_NAME, answers)
    print(f"\n✅ Successfully updated {NLU_FILE} and {RESPONSES_FILE}.")


if __name__ == "__main__":
    run_multilingual_training("How to set up a projector?")
