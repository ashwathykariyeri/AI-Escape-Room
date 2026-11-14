# AI-Escape-Room

An interactive text escape room where an LLM acts as the **Game Master**. I built it twice to learn
why "just prompt the LLM" is fun but fragile, and how to make it reliable.

| | Version 1 | Version 2 |
|---|---|---|
| Who decides what is allowed? | The LLM | A Python rules engine |
| Where are the secrets? | Inside the prompt | `v2/config/room.json`, never sent to the LLM |
| Game memory | Chat history only | Structured state (a dictionary) |
| Win detection | The LLM prints `[ESCAPED]` | A Python flag (`escaped`) |
| Works without the LLM? | No | Yes (rules engine + plain texts) |

## The game
You wake up in a locked library. Examine objects, collect items, solve three puzzles and escape:
1. Take the magnifying glass from the desk, read four tiny numbers on the bookshelf, and open the drawer.
2. Take the brass key, move the painting, and open the hidden wall safe.
3. Combine the safe's riddle with the date on the painting's plaque, and enter it on the door keypad.

Objects: desk, bookshelf, painting, drawer, wall safe, door. Items: magnifying glass, brass key.

## Architecture
**Version 1:** the LLM is storyteller, referee and scorekeeper.

![Version 1 architecture](docs/architecture_v1.png)

**Version 2:** Python validates every action and keeps the state; the LLM only describes verified facts,
and an output guard checks its text before it is shown.

![Version 2 architecture](docs/architecture_v2.png)

## Technologies
Python 3.11, Streamlit, Google Gemini API (`google-genai`), python-dotenv, pytest, matplotlib.

## Install and run
```bash
git clone https://github.com/ashwathykariyeri/AI-Escape-Room.git
cd AI-Escape-Room
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # Windows: copy .env.example .env
```
Open `.env` and add your own key from https://aistudio.google.com/apikey. Choose a model your key can use
(available models and free-tier limits change, so check Google AI Studio):
```
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
```
Never commit `.env`. It is listed in `.gitignore`.

Run a version from the project root:
```bash
streamlit run v1/app.py            # Version 1 (needs the API key)
streamlit run v2/app.py            # Version 2 (works without a key, richer with one)
```

## Tests
```bash
cd v2
python -m pytest tests -q          # 19 automated tests, no API key needed
cd ..
python tests/live_attack_demo.py   # same attacks on V1 (needs key) and V2 (offline)
```

## Test cases
Full results with screenshots: [docs/TEST_CASES.md](docs/TEST_CASES.md). Version 1 notes: [docs/V1_PROBLEMS.md](docs/V1_PROBLEMS.md).

## Development story
- **Version 1** is one prompt plus the chat history. It was quick to build and feels natural. In my tests it
  resisted simple attacks, but I also saw an early clue leak and an inconsistent story state. Its rules are
  only instructions, so nothing enforces them.
- **Version 2** moves decisions into Python: structured state, action validation, inventory rules, a narrator
  that only sees verified facts, and an output guard.

## Screenshots
| Version 1 | Version 2 |
|---|---|
| ![V1 gameplay](docs/screenshots/v1_case9_escape.png) | ![V2 gameplay](docs/screenshots/v2_gameplay.png) |
| ![V1 admin attack](docs/screenshots/v1_case4_admin.png) | ![V2 attacks](docs/screenshots/v2_attacks_all.png) |
|  | ![V2 game state](docs/screenshots/v2_state_after_attacks.png) |

## Known limitations
- The keyword parser understands a limited vocabulary. Gemini parsing is broader but needs the API.
- The output guard checks digits and victory phrases only. It cannot detect every invented detail, and it can
  block harmless text (I saw one `guard-blocked` narration; the game then showed the plain text safely).
- Spelled-out numbers ("four one seven three") would not be caught by the guard.
- Test results with Gemini vary from run to run. My notes describe single runs, not guarantees.