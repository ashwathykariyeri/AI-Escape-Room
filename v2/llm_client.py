"""
llm_client.py  -  the ONLY file that talks to the Gemini API.

Analogy: this is the phone line to the storyteller. Everything else in the
project just says "please call the LLM" and does not care how.
If you switch to another model or provider, you change ONE file.
"""

import os                              # os.getenv reads environment variables
import time                            # time.sleep lets us wait between retries
from dotenv import load_dotenv         # reads the hidden .env file into environment variables

load_dotenv()   # looks for ".env" (searching upwards from this file) and loads it

# Model used when .env has no GEMINI_MODEL line.
DEFAULT_MODEL = "gemini-3.7-flash"


class LLMError(Exception):
    """Our own error type: raised when the LLM call fails (no key, busy server, no internet...)."""


def get_api_key():
    """Return the API key from the environment, or None if there is none."""
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def llm_available() -> bool:
    """True if a key is configured. Offline mode is used when this is False."""
    return bool(get_api_key())


def generate(system: str, prompt: str, json_mode: bool = False, temperature: float = 0.7) -> str:
    """
    Send ONE prompt to Gemini and return the text answer.

    system      : the standing instructions ("you are a game master...")
    prompt      : the actual message for this call
    json_mode   : if True, ask Gemini to answer with valid JSON only
    temperature : creativity (0 = very predictable, 1 = very creative)
    """
    if not llm_available():
        raise LLMError("No GEMINI_API_KEY found. Running in offline mode.")
    try:
        # Imported here (not at the top) so the project still runs if the package is missing.
        from google import genai
        from google.genai import types

        client = genai.Client(
            api_key=get_api_key(),
            http_options=types.HttpOptions(timeout=20000),   # give up after 20 seconds
        )
        config = types.GenerateContentConfig(
            system_instruction=system,                        # the standing rules
            temperature=temperature,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        # Try up to 3 times. A 503 means "server busy", which is often temporary.
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", DEFAULT_MODEL),
                    contents=prompt,
                    config=config,
                )
                return (response.text or "").strip()          # the answer as plain text
            except Exception as exc:
                if "503" in str(exc) and attempt < 2:         # busy, and we still have tries left
                    time.sleep(2 * (attempt + 1))             # wait 2 s, then 4 s
                    continue
                raise                                         # other error, or last try: give up
    except Exception as exc:                                  # any problem -> our own error type
        raise LLMError(str(exc)) from exc