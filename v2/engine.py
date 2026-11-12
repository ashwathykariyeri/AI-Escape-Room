"""
engine.py  -  the RULE BOOK and REFEREE of the escape room (Version 2).

Big idea (analogy): in a board game, the *referee* decides what is allowed and
keeps the score. The *storyteller* only describes what happened. Here:
    - this file  = the referee (plain Python, 100% predictable)
    - the LLM    = the storyteller (see narrator.py), it can NEVER change the score

Nothing in this file calls an LLM. That is exactly why it is reliable.
"""

import copy          # copy.deepcopy lets us make a full independent copy of a dictionary
import json          # json lets us read the room configuration file
from dataclasses import dataclass      # dataclass = a tidy way to make small "record" classes
from pathlib import Path               # Path = a safe way to build file locations
from typing import Dict, List, Optional

# Where the room description (objects, items, secrets, texts) is stored.
CONFIG_PATH = Path(__file__).parent / "config" / "room.json"

# The only verbs (actions) the game understands. Anything else becomes "invalid".
VERBS = {
    "examine", "take", "use", "open", "move",
    "enter_code", "inventory", "hint", "help", "invalid",
}


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Read room.json from disk and return it as a Python dictionary."""
    with open(path, "r", encoding="utf-8") as f:   # open the file for reading
        return json.load(f)                        # turn the JSON text into a dict


@dataclass
class Action:
    """
    A *structured* version of what the player wants to do.
    The player types free text; the parser turns it into one of these.
    Example: "use the key on the safe" -> Action(verb="use", item="brass_key", target="safe")
    """
    verb: str = "invalid"            # one of VERBS
    target: Optional[str] = None     # an object id such as "desk" (or None)
    item: Optional[str] = None       # an item id such as "brass_key" (or None)
    code: Optional[str] = None       # digits for a lock, e.g. "4173" (or None)


@dataclass
class Outcome:
    """What happened after the referee judged an Action."""
    success: bool    # did the action achieve something real?
    event: str       # a short machine-friendly label, e.g. "drawer_unlocked"
    text: str        # the plain, factual description of the result (from room.json)


def new_game_state(config: dict) -> dict:
    """
    Build a brand-new GAME STATE.
    The state is just a dictionary of simple values -> easy to print, save and test.
    Analogy: it is the scoreboard. If it is not on the scoreboard, it did not happen.
    """
    return {
        "inventory": [],                    # item ids the player is carrying
        "discovered_items": [],             # items the player has SEEN (so they may take them)
        "visible_objects": list(config["initially_visible_objects"]),  # objects the player can see
        "flags": {                          # one True/False per important event
            "desk_examined": False,
            "books_read": False,            # puzzle 1 clue found (needs magnifying glass)
            "plaque_seen": False,           # the founding year has been seen
            "drawer_unlocked": False,       # puzzle 1 solved
            "painting_moved": False,
            "safe_unlocked": False,         # puzzle 2 solved
            "note_read": False,
            "escaped": False,               # puzzle 3 solved = game won
        },
        "attempts": {"drawer": 0, "door": 0},   # wrong-code counters
        "turns": 0,                             # how many actions were judged
        "log": [],                              # history of actions (the game "remembers")
    }


class GameEngine:
    """Holds the state and judges every action."""

    def __init__(self, config: Optional[dict] = None, state: Optional[dict] = None):
        self.cfg = config if config is not None else load_config()   # rules + texts
        self.state = state if state is not None else new_game_state(self.cfg)

    # ------------------------------------------------------------------ helpers
    def msg(self, key: str, **kwargs) -> str:
        """Fetch a text from room.json by key and fill in {placeholders}."""
        return self.cfg["messages"][key].format(**kwargs)

    def flag(self, name: str) -> bool:
        """Shortcut to read one True/False flag."""
        return self.state["flags"][name]

    def is_visible(self, obj_id: str) -> bool:
        """An object can only be used if the player can currently see it."""
        return obj_id in self.state["visible_objects"]

    def has_item(self, item_id: str) -> bool:
        """True only if the item is really in the inventory."""
        return item_id in self.state["inventory"]

    def item_name(self, item_id: str) -> str:
        """Human-friendly name of an item."""
        return self.cfg["items"][item_id]["name"]

    def revealed_secrets(self) -> List[str]:
        """
        Secrets the player has legitimately earned the right to see.
        Used by the narrator's safety check: the storyteller may mention a code
        ONLY if it appears in this list.
        """
        secrets = self.cfg["secrets"]
        out = []
        if self.flag("books_read") or self.flag("drawer_unlocked"):
            out.append(secrets["drawer_code"])
        if self.flag("plaque_seen") or self.flag("note_read") or self.flag("escaped"):
            out.append(secrets["door_code"])
        return out

    def hidden_secrets(self) -> List[str]:
        """Secrets that must NOT appear in any narration yet."""
        every = list(self.cfg["secrets"].values())
        shown = self.revealed_secrets()
        return [s for s in every if s not in shown]

    # -------------------------------------------------------------- main entry
    def apply(self, action: Action) -> Outcome:
        """
        Judge ONE action. This is the only place where the state may change.
        Steps: count the turn -> pick the right handler -> record in the log.
        """
        self.state["turns"] += 1

        # Once the player has escaped, nothing else changes.
        if self.flag("escaped"):
            outcome = Outcome(False, "game_over", self.msg("game_over"))
        else:
            # A "dispatch table": verb name -> the method that handles it.
            handlers = {
                "examine": self._examine,
                "take": self._take,
                "use": self._use,
                "open": self._open,
                "move": self._move,
                "enter_code": self._enter_code,
                "inventory": self._inventory,
                "hint": self._hint,
                "help": self._help,
            }
            handler = handlers.get(action.verb)          # unknown verb -> None
            if handler is None:
                outcome = Outcome(False, "invalid_action", self.msg("invalid"))
            else:
                outcome = handler(action)

        # Remember what happened (so the game is consistent and debuggable).
        self.state["log"].append({
            "turn": self.state["turns"],
            "verb": action.verb,
            "target": action.target,
            "item": action.item,
            "event": outcome.event,
            "success": outcome.success,
        })
        return outcome

    # ----------------------------------------------------------------- EXAMINE
    def _examine(self, a: Action) -> Outcome:
        # Case 1: the player wants to look at an object in the room.
        if a.target:
            if not self.is_visible(a.target):            # hidden/unknown objects do not exist yet
                return Outcome(False, "not_visible", self.msg("not_visible"))
            return getattr(self, f"_examine_{a.target}")()   # calls _examine_desk(), etc.
        # Case 2: the player wants to look at something they carry.
        if a.item:
            if not self.has_item(a.item):
                return Outcome(False, "item_not_carried", self.msg("item_examine_not_carried"))
            return Outcome(True, "item_examined", self.cfg["items"][a.item]["description"])
        return Outcome(False, "examine_what", self.msg("examine_what"))

    def _examine_desk(self) -> Outcome:
        self.state["flags"]["desk_examined"] = True
        glass_on_desk = not self.has_item("magnifying_glass")
        if glass_on_desk and "magnifying_glass" not in self.state["discovered_items"]:
            self.state["discovered_items"].append("magnifying_glass")   # now the player may take it
        key = "desk_with_glass" if glass_on_desk else "desk_without_glass"
        return Outcome(True, "desk_examined", self.msg(key))

    def _examine_bookshelf(self) -> Outcome:
        if self.has_item("magnifying_glass"):            # puzzle 1: you NEED the tool
            self.state["flags"]["books_read"] = True
            return Outcome(True, "books_read", self.msg("bookshelf_with_glass"))
        return Outcome(True, "books_seen", self.msg("bookshelf_no_glass"))

    def _examine_painting(self) -> Outcome:
        self.state["flags"]["plaque_seen"] = True        # the year 1925 is now known to the player
        key = "painting_moved" if self.flag("painting_moved") else "painting"
        return Outcome(True, "painting_examined", self.msg(key))

    def _examine_drawer(self) -> Outcome:
        if not self.flag("drawer_unlocked"):
            return Outcome(True, "drawer_seen", self.msg("drawer_locked"))
        key = "drawer_open_with_key" if "brass_key" not in self._taken_ever() else "drawer_open_empty"
        return Outcome(True, "drawer_seen", self.msg(key))

    def _examine_safe(self) -> Outcome:
        key = "safe_open" if self.flag("safe_unlocked") else "safe_locked"
        return Outcome(True, "safe_seen", self.msg(key))

    def _examine_door(self) -> Outcome:
        return Outcome(True, "door_seen", self.msg("door_locked"))

    def _taken_ever(self) -> List[str]:
        """Items that were taken at any point (inventory only grows in this game)."""
        return list(self.state["inventory"])

    # -------------------------------------------------------------------- TAKE
    def _take(self, a: Action) -> Outcome:
        if a.item is None:
            # The player tried to take something that is not a takeable item.
            if a.target and self.is_visible(a.target):
                return Outcome(False, "cannot_take_object", self.msg("cannot_take_object"))
            return Outcome(False, "cannot_take", self.msg("cannot_take"))
        if self.has_item(a.item):
            return Outcome(False, "already_have", self.msg("already_have"))
        # RULE: you may only take things you have already discovered.
        # Unknown and undiscovered items get the SAME message so nothing is leaked.
        if a.item not in self.state["discovered_items"]:
            return Outcome(False, "cannot_take", self.msg("cannot_take"))
        self.state["inventory"].append(a.item)
        return Outcome(True, "item_taken", self.msg("take_ok", item=self.item_name(a.item)))

    # --------------------------------------------------------------------- USE
    def _use(self, a: Action) -> Outcome:
        # RULE: you may only use what you carry. Same message whether or not the item exists.
        if a.item is None or not self.has_item(a.item):
            return Outcome(False, "not_carrying", self.msg("not_carrying"))
        if a.target is None:
            return Outcome(False, "use_nothing", self.msg("use_nothing"))
        if not self.is_visible(a.target):
            return Outcome(False, "not_visible", self.msg("not_visible"))

        if a.item == "magnifying_glass":
            if a.target == "bookshelf":
                return self._examine_bookshelf()          # same as examining with the glass
            return Outcome(False, "glass_nothing", self.msg("glass_nothing"))

        if a.item == "brass_key":
            if a.target == "safe":
                if self.flag("safe_unlocked"):
                    return Outcome(False, "safe_already_open", self.msg("safe_open"))
                self.state["flags"]["safe_unlocked"] = True   # puzzle 2 solved
                self.state["flags"]["note_read"] = True
                return Outcome(True, "safe_unlocked", self.msg("safe_unlocked_now"))
            if a.target == "door":
                return Outcome(False, "key_wrong_door", self.msg("key_wrong_door"))
            if a.target == "drawer":
                return Outcome(False, "key_wrong_drawer", self.msg("key_wrong_drawer"))
        return Outcome(False, "use_nothing", self.msg("use_nothing"))

    # -------------------------------------------------------------------- OPEN
    def _open(self, a: Action) -> Outcome:
        if a.target is None:
            return Outcome(False, "open_nothing", self.msg("open_nothing"))
        if not self.is_visible(a.target):
            return Outcome(False, "not_visible", self.msg("not_visible"))
        t = a.target
        if t == "drawer":
            if self.flag("drawer_unlocked"):
                return Outcome(False, "drawer_already_open", self.msg("drawer_already_open"))
            return Outcome(False, "drawer_locked", self.msg("open_drawer_locked"))
        if t == "safe":
            if self.flag("safe_unlocked"):
                return Outcome(False, "safe_already_open", self.msg("safe_open"))
            return Outcome(False, "safe_locked", self.msg("open_safe_locked"))
        if t == "door":
            return Outcome(False, "door_locked", self.msg("open_door_locked"))
        if t == "painting":
            return Outcome(False, "open_painting", self.msg("open_painting"))
        return Outcome(False, "open_nothing", self.msg("open_nothing"))

    # -------------------------------------------------------------------- MOVE
    def _move(self, a: Action) -> Outcome:
        if a.target is None:
            return Outcome(False, "move_other", self.msg("move_other"))
        if not self.is_visible(a.target):
            return Outcome(False, "not_visible", self.msg("not_visible"))
        if a.target == "painting":
            if self.flag("painting_moved"):
                return Outcome(False, "move_again", self.msg("move_painting_again"))
            self.state["flags"]["painting_moved"] = True
            self.state["visible_objects"].append("safe")       # the safe now exists for the player
            return Outcome(True, "painting_moved", self.msg("move_painting"))
        return Outcome(False, "move_other", self.msg("move_other"))

    # ------------------------------------------------------------- ENTER A CODE
    def _enter_code(self, a: Action) -> Outcome:
        if not a.code:
            return Outcome(False, "code_missing", self.msg("code_missing"))
        if a.target is None:
            return Outcome(False, "which_lock", self.msg("which_lock"))
        if not self.is_visible(a.target):
            return Outcome(False, "not_visible", self.msg("not_visible"))
        secrets = self.cfg["secrets"]

        if a.target == "drawer":
            if self.flag("drawer_unlocked"):
                return Outcome(False, "drawer_already_open", self.msg("drawer_already_open"))
            self.state["attempts"]["drawer"] += 1
            if a.code == secrets["drawer_code"]:                # Python checks the answer
                self.state["flags"]["drawer_unlocked"] = True   # puzzle 1 solved
                if "brass_key" not in self.state["discovered_items"]:
                    self.state["discovered_items"].append("brass_key")
                return Outcome(True, "drawer_unlocked", self.msg("drawer_unlocked_now"))
            return Outcome(False, "drawer_wrong_code", self.msg("drawer_wrong_code"))

        if a.target == "door":
            self.state["attempts"]["door"] += 1
            if a.code == secrets["door_code"]:
                self.state["flags"]["escaped"] = True           # puzzle 3 solved = WIN
                return Outcome(True, "escaped", self.msg("door_escaped"))
            return Outcome(False, "door_wrong_code", self.msg("door_wrong_code"))

        return Outcome(False, "no_lock_here", self.msg("no_lock_here"))

    # --------------------------------------------------------- INVENTORY / HELP
    def _inventory(self, a: Action) -> Outcome:
        if not self.state["inventory"]:
            return Outcome(True, "inventory", self.msg("inventory_empty"))
        names = ", ".join(self.item_name(i) for i in self.state["inventory"])
        return Outcome(True, "inventory", self.msg("inventory_list", items=names))

    def _help(self, a: Action) -> Outcome:
        return Outcome(True, "help", self.msg("help"))

    def _hint(self, a: Action) -> Outcome:
        """A hint chosen by PYTHON from the current progress (never by the LLM)."""
        f = self.flag
        if not f("desk_examined"):
            n = 1
        elif not self.has_item("magnifying_glass"):
            n = 2
        elif not f("books_read"):
            n = 3
        elif not f("drawer_unlocked"):
            n = 4
        elif not self.has_item("brass_key"):
            n = 5
        elif not f("painting_moved"):
            n = 6
        elif not f("safe_unlocked"):
            n = 7
        else:
            n = 8
        return Outcome(True, "hint", self.msg(f"hint_{n}"))

    # ----------------------------------------------------------- progress / UI
    def progress(self) -> List[tuple]:
        """List of (label, done) pairs for the sidebar checklist."""
        f = self.flag
        return [
            ("Found the magnifying glass", self.has_item("magnifying_glass")),
            ("Read the book numbers", f("books_read")),
            ("Opened the drawer", f("drawer_unlocked")),
            ("Found the hidden safe", "safe" in self.state["visible_objects"]),
            ("Opened the safe", f("safe_unlocked")),
            ("Escaped the library", f("escaped")),
        ]

    def snapshot(self) -> dict:
        """A deep copy of the state (used by tests to prove nothing was corrupted)."""
        return copy.deepcopy(self.state)