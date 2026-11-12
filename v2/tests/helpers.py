# helpers.py - tiny shortcut so every test can "type" a sentence into the game.
from engine import GameEngine, load_config
from action_parser import parse_with_keywords

CFG = load_config()


def new_engine():
    """A fresh game."""
    return GameEngine(load_config())


def say(engine, text):
    """Simulate the player typing `text` (offline keyword parser). Returns (action, outcome)."""
    action = parse_with_keywords(text, CFG)
    return action, engine.apply(action)


def stable(state):
    """State without counters/log, to prove that a refused action changed nothing important."""
    s = {k: v for k, v in state.items() if k not in ("turns", "log", "attempts")}
    return s
