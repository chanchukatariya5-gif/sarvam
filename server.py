import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from dotenv import load_dotenv
from sarvamai import SarvamAI
from sarvamai.core.api_error import ApiError

PROJECT_DIR = Path(__file__).resolve().parent
STATIC_DIR = PROJECT_DIR / "static"
load_dotenv(PROJECT_DIR / ".env")

SYSTEM_MESSAGE = (
    "You are a warm, professional patient-coordination assistant in a demo "
    "prototype. Use synthetic scenarios only; do not ask for or repeat real "
    "patient identifiers or medical records. Help with administrative "
    "questions such as preparing for an appointment and explaining general "
    "workflow steps. Do not diagnose, recommend treatment, or claim that an "
    "appointment, reminder, insurance verification, authorization, or claim "
    "action has actually been completed. Explain that this demo is not "
    "connected to clinic, payer, or scheduling systems. For urgent symptoms, "
    "advise contacting local emergency services or a qualified clinician."
)
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}
MAX_REQUEST_BYTES = 64 * 1024
MAX_MESSAGES = 20
MAX_MESSAGE_LENGTH = 4000


class SarvamHandler(BaseHTTPRequestHandler):
    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
            "frame-ancestors 'none'; form-action 'self'",
        )
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_bytes(status, body, "application/json; charset=utf-8")

    def do_GET(self):
        path = urlsplit(self.path).path
        file_info = STATIC_FILES.get(path)
        if file_info is None:
            self.send_json(404, {"error": "Not found."})
            return

        filename, content_type = file_info
        body = (STATIC_DIR / filename).read_bytes()
        self.send_bytes(200, body, content_type)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/chat":
            self.send_json(404, {"error": "Not found."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            self.send_json(400, {"error": "Invalid request."})
            return

        if content_length < 1 or content_length > MAX_REQUEST_BYTES:
            self.send_json(413, {"error": "Request is empty or too large."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "Request must contain valid JSON."})
            return

        messages = payload.get("messages") if isinstance(payload, dict) else None
        if not isinstance(messages, list) or not 1 <= len(messages) <= MAX_MESSAGES:
            self.send_json(400, {"error": "Send between 1 and 20 chat messages."})
            return

        safe_messages = []
        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or message.get("role") not in {"user", "assistant"}
                or not isinstance(message.get("content"), str)
                or not message["content"].strip()
                or len(message["content"]) > MAX_MESSAGE_LENGTH
            ):
                self.send_json(400, {"error": "A chat message is invalid or too long."})
                return
            safe_messages.append(
                {"role": message["role"], "content": message["content"]}
            )

        if safe_messages[-1]["role"] != "user":
            self.send_json(400, {"error": "The latest chat message must be from you."})
            return

        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key:
            self.send_json(
                503,
                {"error": "SARVAM_API_KEY is missing from this project's .env file."},
            )
            return

        try:
            client = SarvamAI(api_subscription_key=api_key)
            response = client.chat.completions(
                model="sarvam-105b-conversations",
                messages=[
                    {"role": "system", "content": SYSTEM_MESSAGE},
                    *safe_messages,
                ],
            )
        except ApiError as error:
            self.log_error("Sarvam API returned an error (status %s).", error.status_code)
            self.send_json(502, {"error": "Sarvam could not complete that request."})
            return
        except httpx.HTTPError as error:
            self.log_error("Network error calling Sarvam (%s).", type(error).__name__)
            self.send_json(502, {"error": "Could not connect to Sarvam. Try again."})
            return

        if not response.choices or not response.choices[0].message.content:
            self.send_json(502, {"error": "Sarvam returned an empty response."})
            return

        self.send_json(200, {"reply": response.choices[0].message.content})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), SarvamHandler)
    print(f"Local Sarvam chat website: http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()
