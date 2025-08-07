#### rasa-automatic-train (Automated Rasa model training using Ollama) ####
-----
Description:
Scripted pipeline to automatically train Rasa NLU models using LLM-generated training data via Ollama or other LLaMA-based inference tools.

README Sections:

🤖 Overview — auto-generate intents & training examples using prompts, then train Rasa.

🛠 Stack — Rasa, Ollama + LLaMA, Python scripting.

✅ Workflow — prompt → generate training JSON → Rasa train → test model.

🧪 Quality Controls — sampling, validation of synthetically generated data.

🚀 Usage Steps — clone repo, set .env with LLM path, run python generate.py, then rasa train.

🏗 Adaptability — extend to new domains, fine-tune prompts, loop for active learning.
