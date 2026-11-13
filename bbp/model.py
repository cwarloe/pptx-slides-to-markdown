"""Format-neutral model of a BBP outline.

Text fields hold light markdown: **bold** and newlines (from <br>).
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
import re

THEMES = {
    "blue": dict(accent="1f5f9e", mid="bcd4ec", soft="dce9f6", faint="eef4fa", ink="12365c", line="8fb0d1"),
    "green": dict(accent="2e7d4f", mid="bfe0cc", soft="dcefe3", faint="eff7f2", ink="17482c", line="93c1a5"),
    "orange": dict(accent="c25e12", mid="f5d2b0", soft="fbe6d2", faint="fdf3ea", ink="6b3207", line="e0b48a"),
    "purple": dict(accent="6b46a8", mid="d9cbee", soft="e8dff6", faint="f5f0fb", ink="3a2266", line="b9a4dc"),
    "gray": dict(accent="4a4f57", mid="d0d3d8", soft="e4e6e9", faint="f3f4f5", ink="23262b", line="a5a9b0"),
}


@dataclass
class Explanation:
    text: str  # e.g. "**The Tackle Line:** below the base of the sternum"
    details: list[str] = field(default_factory=list)


@dataclass
class KeyIdea:
    headline: str
    explanations: list[Explanation] = field(default_factory=list)


@dataclass
class Outline:
    heading: str = "Beyond Bullet Points Outline"  # <h1>
    name: str = ""  # <h2> project name
    audience: str = ""  # <h3> text
    theme: str = "blue"
    headline: str = ""  # title slide headline
    subtitle: str = ""
    acts: list[str] = field(default_factory=lambda: ["ACT 1: SETUP", "ACT 2: DEVELOP THE ACTION", "ACT 3: RESOLUTION"])
    setting: str = ""
    role: str = ""
    point_a: str = ""
    call_to_action: str = ""
    point_b: str = ""
    transitions: list[str] = field(default_factory=list)  # bridging sentences, Transition 1..N
    key_ideas: list[KeyIdea] = field(default_factory=list)
    challenge: str = ""
    action: str = ""
    outcome: str = ""
    closing: str = ""
    footer: str = ""

    def to_dict(self):
        return asdict(self)

    def transition_before_key_idea(self, i: int) -> str | None:
        """Transition 1 follows Act 1; Transition k+1 follows Key Idea k."""
        return self.transitions[i] if i < len(self.transitions) else None


def strip_md(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


def norm(text: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in text.replace("\r", "").split("\n")]
    out = "\n".join(lines).strip()
    return re.sub(r"\n{3,}", "\n\n", out)
