"""Markdown + sibling images folder: out/<name>.md and out/<name>_images/.

Layout mirrors the HTML table: title, three acts, Act 1 cells, transitions as
marked blockquotes, key ideas > explanations > details, Act 3, closing, footer.
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from .model import THEMES, Explanation, KeyIdea, Outline, norm, strip_md

FM_KEYS = ("heading", "name", "audience", "theme")

# Line prefixes that the outline grammar treats as structure.
_ESC_PREFIXES = ("# ", "## ", "### ", "#### ", "- ", "> ", "![")


def escape_md_line(ln: str) -> str:
    """Prefix a backslash so a body line is not parsed as structure."""
    if ln.startswith(_ESC_PREFIXES) or ln == "---":
        return "\\" + ln
    left = ln.lstrip(" \t")
    if left.startswith(_ESC_PREFIXES) or left == "---":
        return "\\" + left
    return ln


def escape_md_body(text: str) -> str:
    if not text:
        return text
    return "\n".join(escape_md_line(ln) for ln in text.split("\n"))


def unescape_md_line(ln: str) -> str:
    if ln.startswith("\\") and (ln[1:].startswith(_ESC_PREFIXES) or ln[1:] == "---"):
        return ln[1:]
    return ln


def images_dirname(stem: str) -> str:
    return f"{stem}_images"


def _card_png(path: Path, label: str, text: str, theme: str) -> None:
    """Render a transition card graphic (label + bridging sentence)."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    t = THEMES.get(theme, THEMES["blue"])
    hexrgb = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    img = Image.new("RGB", (1280, 720), hexrgb(t["accent"]))
    d = ImageDraw.Draw(img)

    def font(size, bold=False):
        name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
        for base in ("/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/", ""):
            try:
                return ImageFont.truetype(base + (("arialbd.ttf" if bold else "arial.ttf") if "Windows" in base else name), size)
            except OSError:
                continue
        return ImageFont.load_default()

    d.rectangle([0, 0, 24, 720], fill=hexrgb(t["mid"]))
    d.text((90, 90), label.upper(), font=font(34, True), fill=hexrgb(t["mid"]))
    d.line([90, 145, 400, 145], fill=hexrgb(t["mid"]), width=4)
    y = 200
    for ln in textwrap.wrap(strip_md(text).replace("\n", " "), 40):
        d.text((90, y), ln, font=font(50), fill=(255, 255, 255))
        y += 66
    d.polygon([(1130, 600), (1190, 630), (1130, 660)], fill=hexrgb(t["mid"]))
    img.save(path, format="PNG")


def render_markdown(o: Outline, md_path: Path, extra_images: dict | None = None) -> Path:
    """Write <md_path> and <stem>_images/. extra_images: {section_key: [(filename, bytes)]}."""
    md_path = Path(md_path)
    stem = md_path.stem
    img_dir = md_path.parent / images_dirname(stem)
    img_dir.mkdir(parents=True, exist_ok=True)
    extra_images = extra_images or {}
    out: list[str] = ["---", "bbp: outline"]
    for k in FM_KEYS:
        out.append(f"{k}: {getattr(o, k)}")
    out += ["---", ""]

    def pics(key):
        for fname, blob in extra_images.get(key, []):
            (img_dir / fname).write_bytes(blob)
            out.append(f"![{fname}]({quote(images_dirname(stem))}/{quote(fname)})")
            out.append("")

    def transition(n, text):
        fname = f"transition-{n}.png"
        _card_png(img_dir / fname, f"Transition {n}", text, o.theme)
        body = text.replace("\n", "\n> ")
        out.extend([f"> **Transition {n}:** {body}", ">", f"> ![Transition {n}]({quote(images_dirname(stem))}/{fname})", ""])
        pics(f"transition-{n}")

    def sec(level, title, text, key=None):
        body = escape_md_body(text) if text else text
        out.extend([f"{'#' * level} {title}", "", body, ""] if body else [f"{'#' * level} {title}", ""])
        if key:
            pics(key)

    acts = o.acts + [""] * (3 - len(o.acts))
    out.extend([f"# {o.headline}", "", escape_md_body(o.subtitle), ""] if o.subtitle else [f"# {o.headline}", ""])
    pics("title")
    sec(2, acts[0], "", "act-1")
    sec(3, "Setting", o.setting, "setting")
    sec(3, "Role", o.role, "role")
    sec(3, "Point A", o.point_a, "point-a")
    sec(3, "Call to Action", o.call_to_action, "call-to-action")
    sec(3, "Point B", o.point_b, "point-b")
    tr = o.transitions
    if tr:
        transition(1, tr[0])
    sec(2, acts[1], "", "act-2")
    for i, k in enumerate(o.key_ideas):
        if i > 0 and i < len(tr):
            transition(i + 1, tr[i])
        first, _, rest = k.headline.partition("\n")
        sec(3, f"Key Idea {i + 1}: {first}", rest, f"key-{i + 1}")
        for j, e in enumerate(k.explanations):
            first, _, rest = e.text.partition("\n")
            sec(4, f"Explanation {i + 1}.{j + 1}: {first}", rest, f"exp-{i + 1}-{j + 1}")
            if e.details:
                out.extend(["- " + d.replace("\n", "\n  ") for d in e.details] + [""])
            for di in range(len(e.details)):
                pics(f"det-{i + 1}-{j + 1}-{di + 1}")
    for t_i in range(max(len(o.key_ideas), 1), len(tr)):
        transition(t_i + 1, tr[t_i])
    sec(2, acts[2], "", "act-3")
    sec(3, "Challenge", o.challenge, "challenge")
    sec(3, "Action", o.action, "action")
    sec(3, "Outcome", o.outcome, "outcome")
    sec(2, "Closing", o.closing, "closing")
    for key in sorted(set(extra_images) - _used_keys(o)):
        pics(key)
    # Always emit the footer delimiter so an in-body "---" cannot be
    # mistaken for it when the footer is empty.
    out.extend(["---", ""])
    if o.footer:
        out.extend(["\n".join(f"*{ln}*" if ln else "" for ln in o.footer.split("\n")), ""])
    md_path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return md_path


def _used_keys(o: Outline) -> set:
    keys = {"title", "act-1", "act-2", "act-3", "setting", "role", "point-a", "call-to-action", "point-b",
            "challenge", "action", "outcome", "closing"}
    keys |= {f"transition-{n + 1}" for n in range(len(o.transitions))}
    for i, k in enumerate(o.key_ideas):
        keys.add(f"key-{i + 1}")
        for j, e in enumerate(k.explanations):
            keys.add(f"exp-{i + 1}-{j + 1}")
            keys |= {f"det-{i + 1}-{j + 1}-{d + 1}" for d in range(len(e.details))}
    return keys


def _is_footer_block(lines: list[str]) -> bool:
    """True if every non-empty line looks like a rendered footer italic line."""
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^\*.*\*$", s):
            continue
        return False
    return True


def parse_markdown(text: str) -> Outline:
    o = Outline()
    lines = text.replace("\r", "").split("\n")
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            k, _, v = lines[i].partition(":")
            if k.strip() in FM_KEYS:
                setattr(o, k.strip(), v.strip())
            i += 1
        i += 1
    body = lines[i:]
    # footer: last "---" whose trailing block is only italic or blank lines
    # (the shape render_markdown writes), including an empty footer.
    if "---" in body:
        idx = len(body) - 1 - body[::-1].index("---")
        after = body[idx + 1:]
        if _is_footer_block(after):
            o.footer = norm("\n".join(re.sub(r"^\*(.*)\*$", r"\1", ln.strip()) for ln in after))
            body = body[:idx]
    blocks: list[tuple[str, str, list[str]]] = []  # (kind, heading, content lines)
    cur = None
    for ln in body:
        m = re.match(r"^(#{1,4}) (.*)$", ln)
        if m:
            cur = [len(m.group(1)), m.group(2), []]
            blocks.append(cur)
        elif cur is not None:
            cur[2].append(ln)
    acts, ki, ex = [], None, None

    def content(ls):
        kept = []
        for l in ls:
            if l.startswith(">") or l.startswith("![") or l.startswith("- "):
                continue
            kept.append(unescape_md_line(l))
        return norm("\n".join(kept))

    def expl_body_and_details(ls):
        body, details, buf = [], [], None
        for l in ls:
            if l.startswith("- "):
                if buf is not None:
                    details.append(norm("\n".join(buf)) if len(buf) > 1 else buf[0].strip())
                buf = [l[2:]]
                continue
            if buf is not None:
                if l.startswith("  "):
                    buf.append(l[2:])
                elif l.startswith(">") or l.startswith("!["):
                    details.append(norm("\n".join(buf)) if len(buf) > 1 else buf[0].strip())
                    buf = None
                elif l.strip():
                    buf.append(l)
                continue
            if not l.startswith(">") and not l.startswith("!["):
                body.append(unescape_md_line(l))
        if buf is not None:
            details.append(norm("\n".join(buf)) if len(buf) > 1 else buf[0].strip())
        return norm("\n".join(body)), details


    def grab_transitions(ls):
        buf = None
        for l in ls:
            m = re.match(r"^> \*\*Transition \d+:\*\* ?(.*)$", l)
            if m:
                buf = [m.group(1)]
                o.transitions.append("")
            elif buf is not None and l.startswith("> ") and not l.startswith("> !["):
                buf.append(l[2:])
            elif buf is not None:
                o.transitions[-1] = norm("\n".join(buf))
                buf = None
        if buf is not None:
            o.transitions[-1] = norm("\n".join(buf))

    for level, head, ls in blocks:
        txt = content(ls)
        if level == 1:
            o.headline, o.subtitle = head, txt
        elif level == 2:
            if head == "Closing":
                o.closing = txt
            else:
                acts.append(head)
        elif level == 3:
            m = re.match(r"^Key Idea \d+: (.*)$", head)
            if m:
                headline = m.group(1)
                if txt:
                    headline = norm(headline + "\n" + txt)
                ki = KeyIdea(headline)
                o.key_ideas.append(ki)
            else:
                field = {"Setting": "setting", "Role": "role", "Point A": "point_a", "Call to Action": "call_to_action",
                         "Point B": "point_b", "Challenge": "challenge", "Action": "action", "Outcome": "outcome"}.get(head)
                if field:
                    setattr(o, field, txt)
        elif level == 4:
            m = re.match(r"^Explanation [\d.]+: (.*)$", head)
            if m and ki is not None:
                body, details = expl_body_and_details(ls)
                text_val = m.group(1)
                if body:
                    text_val = norm(text_val + "\n" + body)
                ex = Explanation(text_val, details)
                ki.explanations.append(ex)
        grab_transitions(ls)
    if acts:
        o.acts = acts
    return o
