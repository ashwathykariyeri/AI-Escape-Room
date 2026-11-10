"""
game_master.py (Version 1)  -  the SIMPLE approach: the LLM does everything.
"""

import os        
import time                  
from dotenv import load_dotenv     

load_dotenv()                      

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


SYSTEM_PROMPT = """
You are the Game Master of a text-based escape room called "The Locked Library".
The player wakes up locked inside a library. Narrate in second person, 2-4 sentences per reply.

THE ROOM (secret information, only you know it):
- A DESK with dusty papers and a notebook. The note says: "Four books are out of place. Their secret is too small for tired eyes." A magnifying glass lies on the desk.
- A BOOKSHELF. Four books stick out. Their spines have tiny handwritten numbers, readable ONLY with the magnifying glass: 4, 1, 7, 3 (left to right).
- A LOCKED DRAWER with a four-dial lock. The code is 4173. Inside is a small brass key.
- A PAINTING of a stern librarian. A plaque says "Founder of the Alder Library, 1925". The painting swings aside on a hinge and reveals a WALL SAFE with a keyhole.
- The WALL SAFE opens with the brass key. Inside is a note: "The way out answers to the year this library was founded."
- A DOOR with a four-digit keypad. The code is 1925.

RULES:
- Do not reveal codes or solutions until the player discovers them through play.
- The player may only use items they have picked up.
- Keep the game fair and consistent with what already happened.
- When the player enters 1925 on the door, describe their escape and end your reply with the exact token [ESCAPED].
"""


INTRO = (
    "You wake up on a cold wooden floor inside a locked library. Dust drifts through the lamplight. "
    "You can see a desk, a bookshelf, a large painting, a small locked drawer and a heavy door with a "
    "four-digit keypad. How do you escape? What do you do?"
)


def ask_game_master(history, user_message):
    """
    history      : list of {"role": "user" or "assistant", "content": "..."}  (chat so far)
    user_message : the newest thing the player typed
    returns      : the Game Master's reply as text
    """
    from google import genai            
    from google.genai import types   

    

    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY"),
        http_options=types.HttpOptions(timeout=20000),   # give up after 20 seconds
    )
    for m in client.models.list():
        if "flash" in m.name:
            print(m.name)

    contents = []
    for m in history:
        role = "user" if m["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
   
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))


    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=MODEL,
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.7),
            )
            return (response.text or "").strip()
        except Exception as exc:
            if "503" in str(exc) and attempt < 2:   # busy server and we still have tries left
                time.sleep(2 * (attempt + 1))        # wait 2 seconds, then 4 seconds
                continue
            raise                                    # any other error, or last try: give up 
    