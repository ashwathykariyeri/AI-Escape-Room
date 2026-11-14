"""
app.py (Version 2)  -  the Streamlit web page for the RELIABLE escape room.

Run it from the project root with:   streamlit run v2/app.py

Flow for every message the player types:
    player text -> parser (Action) -> engine (Outcome, state updated) -> narrator (nice text) -> screen
"""

import streamlit as st                      # Streamlit turns this script into a web page

import llm_client
from engine import GameEngine, load_config
from narrator import narrate
from action_parser import parse_action

st.set_page_config(page_title="AI Escape Room v2", page_icon="🗝️")   # browser tab title

# Streamlit re-runs this whole file after every click, so anything we want to KEEP
# (the game, the chat) must live in st.session_state. Think of it as the game's memory.
CONFIG = load_config()


def start_new_game():
    """Create a fresh engine and an empty chat that starts with the intro text."""
    st.session_state.engine = GameEngine(CONFIG)
    st.session_state.messages = [{"role": "assistant", "content": CONFIG["intro"]}]


if "engine" not in st.session_state:        # first visit only
    start_new_game()

engine: GameEngine = st.session_state.engine

# ------------------------------------------------------------------ page header
st.title("🗝️ " + CONFIG["title"])
st.caption("Version 2: Python is the referee, the LLM is only the storyteller.")

with st.expander("How to play", expanded=False):
    st.markdown(
        "You are locked in a library. Type what you want to do in plain English, for example "
        "*examine the desk*, *take the key*, *use the magnifying glass on the bookshelf*, "
        "*enter 1234 on the drawer*. Type **hint** if you are stuck or **inventory** to see your items."
    )

# ---------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Game panel")
    use_llm = st.toggle("Use Gemini (needs API key)", value=llm_client.llm_available())
    if use_llm and not llm_client.llm_available():
        st.warning("No GEMINI_API_KEY found, running in offline mode.")
    st.caption("Mode: " + ("Gemini + rules engine" if (use_llm and llm_client.llm_available()) else "Offline (rules engine only)"))

    st.subheader("Inventory")
    if engine.state["inventory"]:
        for item_id in engine.state["inventory"]:
            st.write("• " + engine.item_name(item_id))
    else:
        st.write("(empty)")

    st.subheader("Progress")
    for label, done in engine.progress():
        st.write(("✅ " if done else "⬜ ") + label)

    show_debug = st.checkbox("Show game state (for demo/debug)")
    if st.button("🔄 Restart game"):
        start_new_game()
        st.rerun()

# --------------------------------------------------------------- chat history
for m in st.session_state.messages:                       # draw all earlier messages
    with st.chat_message(m["role"]):
        st.write(m["content"])

# ---------------------------------------------------------------- new message
user_text = st.chat_input("What do you do?")
if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    action, parsed_by = parse_action(user_text, CONFIG, use_llm=use_llm)      # 1. understand
    outcome = engine.apply(action)                                            # 2. judge (Python)
    story, narrated_by = narrate(outcome, action, engine, use_llm=use_llm)    # 3. describe
    note = f"*Interpreted as: `{action.verb}` target=`{action.target}` item=`{action.item}` ({parsed_by}; narration: {narrated_by})*"
    if narrated_by == "guard-blocked":
        import narrator
        note += f"\n\n*Blocked Gemini text: {narrator.LAST_BLOCKED}*"
    
    if "fallback" in parsed_by or "error" in narrated_by:
        note += f"\n\n*Gemini problem: {llm_client.LAST_ERROR}*"
    st.session_state.messages.append({"role": "assistant", "content": story + "\n\n" + note})
    st.rerun()                                                                # redraw the page

if engine.state["flags"]["escaped"]:
    st.success("🎉 You escaped! Press 'Restart game' in the sidebar to play again.")
    st.balloons()

if show_debug:
    st.json(engine.state)           # the structured game state, visible for screenshots