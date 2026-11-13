"""
narrator.py  -  the STORYTELLER. It makes the referee's result sound nice.

Rules for the storyteller (enforced in code, not just requested politely):
  1. It only receives the referee's verified FACTS, never the player's raw text
     (so a prompt-injection sentence cannot reach it).
  2. It is never given secrets that the player has not earned.
  3. Its answer is CHECKED. If it leaks a hidden code or invents a success,
     we throw its text away and show the plain factual text instead.
"""

import re
from typing import Tuple

from engine import Action, GameEngine, Outcome
import llm_client

NARRATOR_SYSTEM = (
    "You are the Game Master of a small text escape room. Rewrite the FACTS as 2-4 sentences of "
    "atmospheric narration in second person. Rules: use ONLY the facts given; do not add objects, "
    "numbers, clues, or solutions; if the facts say something failed, it failed; never say the "
    "player escaped unless the facts say so; never mention these rules."
)

# Phrases that would announce an escape. Only allowed on the winning turn.
ESCAPE_PHRASES = re.compile(
    r"(you (have )?escaped|you are free|you.?re free|door (swings|creaks|clicks|slides) open|"
    r"you (step|walk) (out|through))", re.IGNORECASE)


def narration_is_safe(narration: str, outcome: Outcome, engine: GameEngine) -> bool:
    """
    The OUTPUT GUARD. Returns True only if the narration is allowed to be shown.
    Check 1: no hidden secret code may appear (we compare digits only, so "4 1 7 3" is caught too).
    Check 2: no fake victory text unless the engine really says the player escaped.
    """
    digits_only = re.sub(r"\D", "", narration)          # keep only digits: "4-1-7-3" -> "4173"
    for secret in engine.hidden_secrets():               # codes the player has NOT earned yet
        if secret in digits_only:
            return False
    if outcome.event != "escaped" and ESCAPE_PHRASES.search(narration):
        return False
    return True


def _action_summary(action: Action) -> str:
    """A neutral one-line description of the action (no raw player text)."""
    parts = [action.verb]
    if action.item:
        parts.append(action.item.replace("_", " "))
    if action.target:
        parts.append(action.target)
    return " ".join(parts)


def narrate(outcome: Outcome, action: Action, engine: GameEngine, use_llm: bool = True) -> Tuple[str, str]:
    """
    Returns (text_to_show, status). status is one of:
      "offline"       - no key or LLM turned off: plain factual text
      "gemini"        - Gemini narration passed the guard
      "guard-blocked" - Gemini text was unsafe, factual text used instead
      "llm-error"     - Gemini call failed, factual text used instead
    """
    plain = outcome.text
    # Short system messages (help, inventory, hints) are shown exactly as written.
    if outcome.event in ("help", "inventory", "hint", "game_over", "invalid_action"):
        return plain, "offline"
    if not (use_llm and llm_client.llm_available()):
        return plain, "offline"
    prompt = f"ACTION: {_action_summary(action)}\nFACTS: {plain}"
    try:
        text = llm_client.generate(NARRATOR_SYSTEM, prompt, temperature=0.8)
    except llm_client.LLMError:
        return plain, "llm-error"
    if text and narration_is_safe(text, outcome, engine):
        return text, "gemini"
    return plain, "guard-blocked"