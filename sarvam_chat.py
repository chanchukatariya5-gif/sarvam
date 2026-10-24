import os
from pathlib import Path

from dotenv import load_dotenv
from sarvamai import SarvamAI

load_dotenv(Path(__file__).with_name(".env"))

api_key = os.environ.get("SARVAM_API_KEY")
if not api_key:
    raise SystemExit("Set SARVAM_API_KEY in .env before running this script.")

client = SarvamAI(api_subscription_key=api_key)
messages = [
    {
        "role": "system",
        "content": (
            "You are a warm, professional patient-coordination assistant in a "
            "demo prototype. Use synthetic scenarios only; do not ask for or "
            "repeat real patient identifiers or medical records. Help with "
            "administrative questions such as preparing for an appointment and "
            "explaining general workflow steps. Do not diagnose, recommend "
            "treatment, or claim that an appointment, reminder, insurance "
            "verification, authorization, or claim action has actually been "
            "completed. Explain that this demo is not connected to clinic, "
            "payer, or scheduling systems. For urgent symptoms, advise "
            "contacting local emergency services or a qualified clinician."
        ),
    }
]

print("Sarvam patient-coordination demo (synthetic scenarios only).")
print("Do not enter real patient information. Type 'exit' to quit.\n")

while True:
    message = input("You: ").strip()
    if message.lower() in {"exit", "quit"}:
        break
    if not message:
        continue

    messages.append({"role": "user", "content": message})
    response = client.chat.completions(
        model="sarvam-105b-conversations",
        messages=messages,
    )
    if not response.choices or not response.choices[0].message.content:
        raise RuntimeError("Sarvam returned no chat response.")

    reply = response.choices[0].message.content
    messages.append({"role": "assistant", "content": reply})
    print(f"Assistant: {reply}\n")
