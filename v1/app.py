"""
app.py (Version 1)  -  Streamlit page for the simple LLM-only escape room.
Run it with:   streamlit run v1/app.py
"""

import os
import streamlit as st
from dotenv import load_dotenv

from game_master import INTRO, ask_game_master

load_dotenv()
st.set_page_config(page_title="AI Escape Room v1", page_icon="🗝️")

st.title("🗝️ The Locked Library (Version 1)")
st.caption("Version 1: the LLM is storyteller AND referee. Fun, but easy to break.")

with st.expander("How to play", expanded=False):
    st.markdown("Type what you want to do, e.g. *I examine the bookshelf*. The AI Game Master replies. "
                "Find clues, solve the puzzles and escape through the door.")

# Stop early with a friendly message if no API key is configured.
if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
    st.error("No API key found. Copy .env.example to .env and add your GEMINI_API_KEY (see README).")
    st.stop()


def restart():
    """Clear the chat and start over."""
    st.session_state.messages = [{"role": "assistant", "content": INTRO}]
    st.session_state.escaped = False


if "messages" not in st.session_state:
    restart()

with st.sidebar:
    if st.button("🔄 Restart game"):
        restart()
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.write(m["content"])

user_text = st.chat_input("What do you do?")
if user_text and not st.session_state.escaped:
    history = list(st.session_state.messages)             # everything said so far (before this turn)

    try:
        reply = ask_game_master(history, user_text)       # ask Gemini
    except Exception as exc:
        st.error(f"The Game Master could not answer. Please try again. ({exc})")
        st.stop()                                         # stop here: failed turn is NOT saved

    # Only reached if Gemini answered successfully, so now save the player's message.
    st.session_state.messages.append({"role": "user", "content": user_text})

    if "[ESCAPED]" in reply:                              # win detection (fragile, relies on the LLM)
        st.session_state.escaped = True
        reply = reply.replace("[ESCAPED]", "").strip()
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.rerun()

if st.session_state.get("escaped"):
    st.success("🎉 You escaped! Press Restart game to play again.")
