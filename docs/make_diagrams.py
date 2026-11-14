"""
make_diagrams.py - draws the two architecture diagrams as PNG files.
Run from the project root:  python docs/make_diagrams.py
"""
import matplotlib
matplotlib.use("Agg")                       # draw straight to files, no window needed
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


def box(ax, x, y, w, h, text, color):
    """Draw a rounded rectangle with centred text."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02", fc=color, ec="#333", lw=1.4))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=10)


def arrow(ax, x1, y1, x2, y2, label=""):
    """Draw an arrow with an optional label."""
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", lw=1.6, color="#333"))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.12, label, ha="center", fontsize=8, color="#444")


# ---------------- Version 1 ----------------
fig, ax = plt.subplots(figsize=(10, 3.2)); ax.set_xlim(0, 11); ax.set_ylim(0.2, 3.4); ax.axis("off")
ax.set_title("Version 1 - LLM does everything", fontsize=12, fontweight="bold")
box(ax, 0.1, 1.4, 1.7, 1.0, "Player\n(browser)", "#e8f1ff")
box(ax, 2.6, 1.4, 2.1, 1.0, "Streamlit UI\n+ chat history", "#e9f7ec")
box(ax, 5.6, 1.4, 2.3, 1.0, "Gemini LLM\nstory + rules +\nsecrets + memory", "#fff3d6")
box(ax, 8.7, 1.4, 2.2, 1.0, "Reply shown\n[ESCAPED] token\ncheck", "#f3e8ff")
arrow(ax, 1.8, 1.9, 2.6, 1.9, "text")
arrow(ax, 4.7, 1.9, 5.6, 1.9, "chat")
arrow(ax, 7.9, 1.9, 8.7, 1.9, "reply")
ax.text(5.5, 0.7, "Secrets and rules sit inside one prompt. Nothing outside the LLM checks its decisions.",
        ha="center", fontsize=9, style="italic")
fig.savefig("docs/architecture_v1.png", dpi=160, bbox_inches="tight"); plt.close(fig)

# ---------------- Version 2 ----------------
fig, ax = plt.subplots(figsize=(10, 5.6)); ax.set_xlim(0, 11); ax.set_ylim(0.6, 6.4); ax.axis("off")
ax.set_title("Version 2 - Python is the referee, the LLM only narrates", fontsize=12, fontweight="bold")
# top row: the request travels left -> right
box(ax, 0.1, 3.8, 1.7, 1.0, "Player\n(browser)", "#e8f1ff")
box(ax, 2.4, 3.8, 2.0, 1.0, "Streamlit UI\n(app.py)", "#e9f7ec")
box(ax, 5.0, 3.8, 2.4, 1.0, "Action parser\nLLM -> JSON, or\nkeyword fallback", "#fff3d6")
box(ax, 8.0, 3.8, 2.8, 1.0, "Rules engine\n(engine.py)\nvalidates every action", "#ffe0e0")
# above and below the engine: configuration and state
box(ax, 8.0, 5.4, 2.8, 0.8, "room.json: rules, secrets,\nfact texts", "#f0f0f0")
box(ax, 8.0, 2.0, 2.8, 1.1, "Game state (dict)\ninventory, flags,\nattempts, log", "#e0f7f7")
# bottom row: the answer travels right -> left
box(ax, 5.0, 2.0, 2.4, 1.0, "Narrator (LLM)\nsees verified facts only", "#fff3d6")
box(ax, 2.0, 2.0, 2.4, 1.0, "Output guard\nblocks leaked codes /\nfake victory", "#f3e8ff")
arrow(ax, 1.8, 4.3, 2.4, 4.3)
arrow(ax, 4.4, 4.3, 5.0, 4.3, "text")
arrow(ax, 7.4, 4.3, 8.0, 4.3, "Action")
arrow(ax, 9.4, 5.4, 9.4, 4.8, "")
arrow(ax, 9.4, 3.8, 9.4, 3.1, "")
ax.text(9.55, 3.4, "read / write", fontsize=8, color="#444")
arrow(ax, 8.0, 3.8, 7.4, 2.9, "")
ax.text(7.55, 3.45, "Outcome (facts)", fontsize=8, color="#444", ha="right")
arrow(ax, 5.0, 2.5, 4.4, 2.5, "story")
arrow(ax, 3.2, 3.0, 3.2, 3.8, "")
ax.text(3.3, 3.35, "safe text", fontsize=8, color="#444")
ax.text(0.2, 1.3, "Player text never reaches the narrator, and codes are extracted by Python, not by the LLM.",
        fontsize=9, style="italic")
fig.savefig("docs/architecture_v2.png", dpi=160, bbox_inches="tight"); plt.close(fig)
print("diagrams written")