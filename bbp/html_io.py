"""Read and write the docs/bbp-outline.html table format."""
from __future__ import annotations

import html as htmllib
from pathlib import Path
import re

from bs4 import BeautifulSoup, NavigableString, Tag

from .model import Explanation, KeyIdea, Outline, norm

STYLE = (Path(__file__).parent / "assets" / "bbp-style.html").read_text(encoding="utf-8")


def _cell_md(td: Tag) -> str:
    parts: list[str] = []

    def walk(node):
        for ch in node.children:
            if isinstance(ch, NavigableString):
                parts.append(re.sub(r"\s+", " ", str(ch)))
            elif isinstance(ch, Tag):
                if ch.name == "br":
                    parts.append("\n")
                elif ch.name == "span" and "label" in (ch.get("class") or []):
                    continue
                elif ch.name in ("strong", "b"):
                    parts.append("**" + " ".join(ch.get_text(" ").split()) + "**")
                elif ch.name == "li":
                    if parts and not parts[-1].endswith("\n"):
                        parts.append("\n")
                    walk(ch)
                    if not parts or not parts[-1].endswith("\n"):
                        parts.append("\n")
                else:
                    walk(ch)

    walk(td)
    return norm("".join(parts))


def _wrap_md(nodes) -> str:
    wrap = BeautifulSoup("<td></td>", "html.parser").td
    for n in nodes:
        wrap.append(n)
    return _cell_md(wrap)


def _title_headline_subtitle(td: Tag) -> tuple[str, str]:
    """Split a TITLE cell, unwrapping the outer <strong> the renderer adds."""
    td = BeautifulSoup(str(td), "html.parser").td
    before, after, seen_br = [], [], False
    for ch in list(td.children):
        if isinstance(ch, Tag) and ch.name == "br":
            seen_br = True
            continue
        (after if seen_br else before).append(ch)
    if (len(before) == 1 and isinstance(before[0], Tag)
            and before[0].name in ("strong", "b")):
        headline = _cell_md(before[0])
    else:
        headline = _wrap_md(before)
    return headline, _wrap_md(after)


def parse_html(src: str) -> Outline:
    soup = BeautifulSoup(src, "html.parser")
    o = Outline()
    body = soup.body or soup
    o.theme = (body.get("data-theme") if isinstance(body, Tag) else None) or "blue"
    if soup.h1:
        o.heading = " ".join(soup.h1.get_text(" ").split())
    if soup.h2:
        o.name = " ".join(soup.h2.get_text(" ").split())
    if soup.h3:
        o.audience = " ".join(soup.h3.get_text(" ").split())
    table = soup.find("table", class_="bbp-table")
    if table is None:
        raise ValueError("no <table class='bbp-table'> found")
    acts: list[str] = []
    pending = None
    ki = ex = None
    for tr in table.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        classes = [set(td.get("class") or []) for td in tds]
        if all("section-header" in c for c in classes):
            label = " ".join(td.get_text(" ") for td in tds).lower()
            if label.strip() == "title":
                pending = "title"
            elif "setting" in label:
                pending = "setting"
            elif "point a" in label:
                pending = "points"
            elif "challenge" in label:
                pending = "act3"
            elif "closing" in label:
                pending = "closing"
            else:
                pending = None  # e.g. Key Idea / Explanation / Details column labels
            continue
        if "act-header" in classes[0]:
            acts.append(" ".join(tds[0].get_text(" ").split()))
            continue
        if "transition-cell" in classes[0]:
            o.transitions.append(_cell_md(tds[0]))
            continue
        if "footer-text" in classes[0]:
            o.footer = _cell_md(tds[0])
            continue
        cells = [_cell_md(td) for td in tds]
        if pending == "title":
            first, rest = _title_headline_subtitle(tds[0])
            o.headline = first
            o.subtitle = rest
        elif pending == "setting":
            o.setting, o.role = cells[0], cells[1]
        elif pending == "points":
            o.point_a, o.call_to_action, o.point_b = cells[:3]
        elif pending == "act3":
            o.challenge, o.action, o.outcome = cells[:3]
        elif pending == "closing":
            o.closing = cells[0]
        else:
            for td, txt in zip(tds, cells):
                c = td.get("class") or []
                if "key-idea-cell" in c:
                    ki = KeyIdea(txt)
                    o.key_ideas.append(ki)
                elif "explanation-cell" in c:
                    ex = Explanation(txt)
                    ki.explanations.append(ex)
                elif ex is not None:
                    ex.details.append(txt)
            continue
        pending = None
    if acts:
        o.acts = acts
    return o


def _md_inline_to_html(text: str) -> str:
    import re

    esc = htmllib.escape(text, quote=True)
    esc = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", esc)
    return esc.replace("\n", "<br />")


def render_html(o: Outline) -> str:
    h = _md_inline_to_html
    r: list[str] = []
    a = r.append
    a("<!doctype html>\n<html>\n<head>\n<meta charset=\"UTF-8\" />")
    a(f"<title>BBP Outline - {htmllib.escape(o.name)}</title>")
    a(STYLE.rstrip())
    a(f"</head>\n<body data-theme=\"{htmllib.escape(o.theme)}\">")
    a(f"<h1>{h(o.heading)}</h1>\n<h2>{h(o.name)}</h2>")
    if o.audience:
        a(f"<h3>{h(o.audience)}</h3>")
    a('<table class="bbp-table">\n<colgroup><col style="width: 30%" /><col style="width: 30%" /><col style="width: 40%" /></colgroup>')
    row = lambda *cells: a("<tr>" + "".join(cells) + "</tr>")
    full = lambda cls, body: row(f'<td colspan="3"{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>{body}</td>')
    sh = lambda t, extra="": f'<td class="section-header"{extra}>{t}</td>'
    td = lambda t, extra="": f"<td{extra}>{t}</td>"
    lab = lambda t: f'<span class="label">{t}</span>'
    full("section-header", "TITLE")
    full("", f"<strong>{h(o.headline)}</strong>" + (f"<br />{h(o.subtitle)}" if o.subtitle else ""))
    acts = o.acts + [""] * (3 - len(o.acts))
    full("act-header", h(acts[0]))
    row(sh("Setting"), sh("Role", ' colspan="2"'))
    row(td(h(o.setting)), td(h(o.role), ' colspan="2"'))
    row(sh("Point A (Where am I?)"), sh("Call to Action (How do I get from A to B?)"), sh("Point B (Where do I want to be?)"))
    row(td(h(o.point_a)), td(h(o.call_to_action)), td(h(o.point_b)))
    trans = list(o.transitions)
    if trans:
        full("transition-cell", lab("Transition 1") + h(trans[0]))
    full("act-header", h(acts[1]))
    row(sh("Key Idea (5 minutes)"), sh("Explanation (15 minutes)"), sh("Details (45 minutes)"))
    for i, k in enumerate(o.key_ideas):
        if i > 0 and i < len(trans):
            full("transition-cell", lab(f"Transition {i + 1}") + h(trans[i]))
        n = sum(max(1, len(e.details)) for e in k.explanations) or 1
        first = True
        for j, e in enumerate(k.explanations):
            dets = e.details or [""]
            for d_i, d in enumerate(dets):
                cells = []
                if first:
                    cells.append(f'<td rowspan="{n}" class="key-idea-cell">{lab(f"Key Idea {i + 1}")}{h(k.headline)}</td>')
                    first = False
                if d_i == 0:
                    cells.append(f'<td rowspan="{len(dets)}" class="explanation-cell">{lab(f"Explanation {j + 1}")}{h(e.text)}</td>')
                cells.append(td(h(d)))
                row(*cells)
    for t_i in range(max(len(o.key_ideas), 1), len(trans)):
        full("transition-cell", lab(f"Transition {t_i + 1}") + h(trans[t_i]))
    full("act-header", h(acts[2]))
    row(sh("Challenge (Recap)"), sh("Action"), sh("Outcome"))
    row(td(h(o.challenge)), td(h(o.action)), td(h(o.outcome)))
    full("section-header", "CLOSING LINE")
    full("", h(o.closing))
    full("footer-text", h(o.footer))
    a("</table>\n</body>\n</html>\n")
    return "\n".join(r)
