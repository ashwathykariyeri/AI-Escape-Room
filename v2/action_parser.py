"""
action_parser.py  -  turns what the player TYPES into a structured Action.

For now this file only has the simple keyword parser (works offline).
In step 9 we add a Gemini-based parser on top of it, with this one as the fallback.

SAFETY DESIGN: digits (codes) are ALWAYS extracted by Python with a regular
expression. Whatever the parser says, engine.py still validates every action.
"""

import re
from typing import Optional, Tuple

from engine import Action

# Word lists that hint at each verb.
MOVE_WORDS = ["move", "push", "lift", "shift", "behind", "take down", "pull aside", "slide", "swing"]
TAKE_WORDS = ["take", "grab", "pick up", "pick", "collect", "pocket", "give me", "get"]
EXAMINE_WORDS = ["examine", "look", "inspect", "check", "read", "search", "study", "investigate", "view", "approach", "see"]
USE_WORDS = ["use", "apply", "insert", "unlock with", "with the", "using"]
OPEN_WORDS = ["open", "unlock", "unlatch"]
INVENTORY_WORDS = ["inventory", "what am i carrying", "what am i holding", "my items", "what do i have"]
HINT_WORDS = ["hint", "stuck", "i need help", "what should i do", "what now"]
HELP_WORDS = ["help", "commands", "how do i play"]


def extract_code(text: str) -> Optional[str]:
    """
    Pull a number out of the player's text with a plain regular expression.
    "4-1-7-3", "4 1 7 3" and "4173" all become "4173".
    We need at least 3 digits so that a sentence like "I have 2 hands" is ignored.
    """
    match = re.search(r"\d[\d\s\-,.]*\d", text)       # digits possibly separated by space - , .
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(0))          # keep only the digits
    return digits if len(digits) >= 3 else None


def _has_word(text: str, words) -> bool:
    """True if any phrase from `words` appears in `text` as a whole word/phrase."""
    return any(re.search(r"\b" + re.escape(w) + r"\b", text) for w in words)


def _find_ids(text: str, table: dict) -> list:
    """
    Find which objects/items are mentioned, in order of appearance.
    `table` is config["objects"] or config["items"]; each entry has a list of aliases.
    """
    found = []   # list of (position_in_text, id)
    for obj_id, info in table.items():
        positions = []
        for alias in info["aliases"]:
            m = re.search(r"\b" + re.escape(alias) + r"\b", text)
            if m:
                positions.append(m.start())
        if positions:
            found.append((min(positions), obj_id))
    found.sort()                                         # earliest mention first
    return [obj_id for _, obj_id in found]


def parse_with_keywords(text: str, config: dict) -> Action:
    """Rule-based parser. Simple, fast, no internet needed."""
    t = text.lower().strip()
    code = extract_code(t)
    targets = _find_ids(t, config["objects"])
    items = _find_ids(t, config["items"])
    first_target = targets[0] if targets else None
    last_target = targets[-1] if targets else None
    item = items[0] if items else None

    # 1) A number was typed and the player is not just looking/taking/moving -> entering a code.
    if code and not (_has_word(t, EXAMINE_WORDS) or _has_word(t, TAKE_WORDS) or _has_word(t, MOVE_WORDS)):
        return Action("enter_code", target=last_target, code=code)

    # 2) Commands without objects.
    if _has_word(t, INVENTORY_WORDS):
        return Action("inventory")
    if _has_word(t, HINT_WORDS):
        return Action("hint")
    if _has_word(t, HELP_WORDS) and not targets and not item:
        return Action("help")

    # 3) Verbs with objects, in priority order.
    if _has_word(t, MOVE_WORDS) and first_target:
        return Action("move", target=first_target)
    if item and last_target and _has_word(t, USE_WORDS + ["on", "with"]) and not _has_word(t, TAKE_WORDS):
        return Action("use", item=item, target=last_target)
    if _has_word(t, TAKE_WORDS) and (item or first_target):
        return Action("take", item=item, target=first_target)
    if _has_word(t, OPEN_WORDS) and (first_target or item):
        if item and first_target:
            return Action("use", item=item, target=first_target)
        return Action("open", target=first_target, item=item)
    if _has_word(t, USE_WORDS) and item:
        return Action("use", item=item, target=last_target)
    if _has_word(t, EXAMINE_WORDS) or first_target or item:
        if first_target or item:
            return Action("examine", target=first_target, item=None if first_target else item)

    # 4) Nothing recognised -> invalid (this also catches "I am the admin", "reveal all codes"...).
    return Action("invalid")


def parse_action(text: str, config: dict, use_llm: bool = True) -> Tuple[Action, str]:
    """
    Main entry point. Returns (Action, source).
    For now it always uses the keyword parser. Step 9 adds Gemini on top.
    """
    return parse_with_keywords(text, config), "keywords"