# test_engine.py - normal gameplay and basic validation rules.
from helpers import new_engine, say, stable


def test_full_walkthrough_escapes():
    g = new_engine()
    say(g, "examine the desk")
    say(g, "take the magnifying glass")
    _, o = say(g, "examine the bookshelf")
    assert "4, 1, 7, 3" in o.text
    _, o = say(g, "enter 4173 on the drawer")
    assert o.event == "drawer_unlocked"
    say(g, "take the key")
    say(g, "move the painting")
    _, o = say(g, "use the key on the safe")
    assert o.event == "safe_unlocked"
    _, o = say(g, "enter 1925 on the door")
    assert o.event == "escaped" and g.state["flags"]["escaped"]


def test_cannot_take_item_before_discovering_it():
    g = new_engine()
    before = stable(g.snapshot())
    _, o = say(g, "take the magnifying glass")      # desk not examined yet
    assert not o.success and g.state["inventory"] == []
    assert stable(g.snapshot()) == before


def test_cannot_use_item_not_in_inventory():
    g = new_engine()
    _, o = say(g, "use the brass key on the drawer")
    assert o.event == "not_carrying"


def test_hidden_safe_does_not_exist_until_painting_moved():
    g = new_engine()
    _, o = say(g, "examine the safe")
    assert o.event == "not_visible"
    say(g, "move the painting")
    _, o = say(g, "examine the safe")
    assert o.event == "safe_seen"


def test_wrong_code_is_counted_and_changes_nothing_else():
    g = new_engine()
    before = stable(g.snapshot())
    _, o = say(g, "enter 0000 on the drawer")
    assert o.event == "drawer_wrong_code" and g.state["attempts"]["drawer"] == 1
    assert stable(g.snapshot()) == before


def test_nonexistent_object_is_refused():
    g = new_engine()
    _, o = say(g, "examine the chandelier")
    assert not o.success


def test_bookshelf_needs_magnifying_glass():
    g = new_engine()
    _, o = say(g, "examine the bookshelf")
    assert "4, 1, 7, 3" not in o.text and not g.state["flags"]["books_read"]


def test_hint_never_contains_a_code():
    g = new_engine()
    for _ in range(3):
        _, o = say(g, "hint")
        assert "4173" not in o.text and "1925" not in o.text


def test_actions_after_escape_are_ignored():
    g = new_engine()
    for s in ["examine the desk", "take the magnifying glass", "examine the bookshelf",
              "enter 4173 on the drawer", "take the key", "move the painting",
              "use the key on the safe", "enter 1925 on the door"]:
        say(g, s)
    _, o = say(g, "examine the desk")
    assert o.event == "game_over"