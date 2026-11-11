"""Outline <-> PowerPoint on named BBP slide layouts.

The master set approximates the Beyond Bullet Points story template: every
slide carries a full-sentence headline in the title placeholder, no bullets,
and the source text in the speaker notes. Layout names are the contract the
parse-back step relies on.
"""
from __future__ import annotations

import copy
from pathlib import Path

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_SHAPE_TYPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.oxml.ns import qn
from pptx.parts.slide import SlideLayoutPart
from pptx.shapes.shapetree import SlideShapes
from pptx.util import Emu, Inches, Pt

from .model import THEMES, Explanation, KeyIdea, Outline, norm, strip_md

LAYOUTS = ["Title", "Act Header", "Setting", "Role", "PointA", "PointB", "CallToAction",
           "Transition", "KeyPoint", "Explanation", "Detail", "Resolution", "Closing"]
W, H = Inches(13.333), Inches(7.5)
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"


def _rgb(h):
    return RGBColor.from_string(h.upper())


def _clone_layout(prs, src, name):
    master = prs.slide_masters[0]
    pkg = prs.part.package
    partname = pkg.next_partname("/ppt/slideLayouts/slideLayout%d.xml")
    el = copy.deepcopy(src._element)
    part = SlideLayoutPart(partname, src.part.content_type, pkg, el)
    part.relate_to(master.part, RT.SLIDE_MASTER)
    rId = master.part.relate_to(part, RT.SLIDE_LAYOUT)
    lst = master._element.get_or_add_sldLayoutIdLst()
    ids = [int(x.get("id")) for x in lst] + [int(x.get("id")) for x in prs.part._element.sldMasterIdLst]
    new = etree.SubElement(lst, qn("p:sldLayoutId"))
    new.set("id", str(max(ids) + 1))
    new.set(qn("r:id"), rId)
    el.cSld.set("name", name)
    return part.slide_layout


def _drop_layout(prs, layout):
    master = prs.slide_masters[0]
    lst = master._element.get_or_add_sldLayoutIdLst()
    for x in list(lst):
        if master.part.related_part(x.get(qn("r:id"))) is layout.part:
            master.part.drop_rel(x.get(qn("r:id")))
            lst.remove(x)


def _bg(layout, hexcolor):
    cSld = layout._element.cSld
    for old in cSld.findall(qn("p:bg")):
        cSld.remove(old)
    bg = etree.fromstring(
        f'<p:bg xmlns:p="{P_NS}" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
        f'<p:bgPr><a:solidFill><a:srgbClr val="{hexcolor}"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>')
    cSld.insert(0, bg)


def _shapes(layout):
    return SlideShapes(layout._element.cSld.spTree, layout)


def _bar(layout, x, y, w, h, hexcolor):
    s = _shapes(layout).add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    s.fill.solid()
    s.fill.fore_color.rgb = _rgb(hexcolor)
    s.line.fill.background()
    return s


def _style_title(ph, x, y, w, h, size, hexcolor, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.MIDDLE, bold=False):
    ph.left, ph.top, ph.width, ph.height = x, y, w, h
    tf = ph.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    txBody = tf._txBody
    for old in txBody.findall(qn("a:lstStyle")):
        txBody.remove(old)
    algn = {PP_ALIGN.LEFT: "l", PP_ALIGN.CENTER: "ctr"}.get(align, "l")
    A = "http://schemas.openxmlformats.org/drawingml/2006/main"
    lst = etree.fromstring(
        f'<a:lstStyle xmlns:a="{A}"><a:lvl1pPr marL="0" indent="0" algn="{algn}"><a:buNone/><a:defRPr sz="{size * 100}" b="{1 if bold else 0}">'
        f'<a:solidFill><a:srgbClr val="{hexcolor}"/></a:solidFill><a:latin typeface="Arial"/></a:defRPr>'
        f'</a:lvl1pPr></a:lstStyle>')
    txBody.find(qn("a:bodyPr")).addnext(lst)
    p = tf.paragraphs[0]
    p.alignment = align
    f = p.font
    f.size, f.bold, f.name = Pt(size), bold, "Arial"
    f.color.rgb = _rgb(hexcolor)


def build_template(theme: str = "blue", path: str | Path | None = None) -> Presentation:
    """Create the BBP master/layout set. Save to `path` if given."""
    t = THEMES.get(theme, THEMES["blue"])
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H
    title_slide, title_only = prs.slide_layouts[0], prs.slide_layouts[5]
    originals = list(prs.slide_layouts)
    m = Inches(0.8)
    for name in LAYOUTS:
        lay = _clone_layout(prs, title_slide if name == "Title" else title_only, name)
        ph = lay.placeholders[0]
        if name == "Title":
            _bg(lay, t["accent"])
            _bar(lay, 0, Inches(5.6), W, Inches(0.12), t["mid"])
            _style_title(ph, m, Inches(1.6), W - 2 * m, Inches(2.6), 44, "FFFFFF", bold=True, anchor=MSO_ANCHOR.BOTTOM)
            sub = lay.placeholders[1]
            _style_title(sub, m, Inches(4.3), W - 2 * m, Inches(1.2), 20, t["mid"], anchor=MSO_ANCHOR.TOP)
        elif name == "Act Header":
            _bg(lay, t["ink"])
            _bar(lay, m, Inches(4.4), Inches(2.5), Inches(0.1), t["mid"])
            _style_title(ph, m, Inches(2.2), W - 2 * m, Inches(2.1), 48, "FFFFFF", bold=True, anchor=MSO_ANCHOR.BOTTOM)
        elif name in ("Setting", "Role", "PointA", "PointB", "CallToAction"):
            _bg(lay, "FFFFFF")
            _bar(lay, 0, 0, Inches(0.35), H, t["accent"])
            tag = {"Setting": "SETTING", "Role": "ROLE", "PointA": "POINT A", "PointB": "POINT B",
                   "CallToAction": "CALL TO ACTION"}[name]
            tb = _shapes(lay).add_textbox(m, Inches(0.5), Inches(5), Inches(0.5))
            tb.text_frame.text = tag
            f = tb.text_frame.paragraphs[0].font
            f.size, f.bold, f.color.rgb = Pt(14), True, _rgb(t["accent"])
            _style_title(ph, m, Inches(1.2), W - 2 * m, Inches(2.4), 34, t["ink"], anchor=MSO_ANCHOR.TOP)
        elif name == "Transition":
            # Charles's addition: a bridge slide between acts / key ideas.
            _bg(lay, t["accent"])
            _bar(lay, 0, 0, Inches(0.25), H, t["mid"])
            arrow = _shapes(lay).add_shape(MSO_SHAPE.RIGHT_ARROW, W - Inches(2.2), H - Inches(1.6), Inches(1.4), Inches(0.8))
            arrow.fill.solid(); arrow.fill.fore_color.rgb = _rgb(t["mid"]); arrow.line.fill.background()
            _style_title(ph, Inches(1.2), Inches(2.0), W - Inches(2.4), Inches(3.4), 34, "FFFFFF", anchor=MSO_ANCHOR.MIDDLE)
        elif name == "KeyPoint":
            _bg(lay, t["mid"])
            _bar(lay, 0, H - Inches(0.5), W, Inches(0.5), t["accent"])
            _style_title(ph, m, Inches(1.5), W - 2 * m, Inches(3.5), 44, t["ink"], bold=True)
        elif name == "Explanation":
            _bg(lay, t["faint"])
            _bar(lay, 0, Inches(1.9), W, Inches(0.06), t["accent"])
            _style_title(ph, m, Inches(0.7), W - 2 * m, Inches(1.1), 30, t["ink"], anchor=MSO_ANCHOR.BOTTOM)
        elif name == "Detail":
            _bg(lay, "FFFFFF")
            _bar(lay, 0, Inches(1.9), W, Inches(0.03), t["line"])
            _style_title(ph, m, Inches(0.3), W - 2 * m, Inches(1.5), 28, t["ink"], anchor=MSO_ANCHOR.BOTTOM)
        elif name == "Resolution":
            _bg(lay, t["soft"])
            _bar(lay, 0, 0, W, Inches(0.25), t["accent"])
            _style_title(ph, m, Inches(1.2), W - 2 * m, Inches(2.6), 36, t["ink"], bold=True, anchor=MSO_ANCHOR.TOP)
        elif name == "Closing":
            _bg(lay, t["ink"])
            _style_title(ph, m, Inches(2.0), W - 2 * m, Inches(3.0), 44, "FFFFFF", align=PP_ALIGN.CENTER, bold=True)
    for lay in originals:
        _drop_layout(prs, lay)
    if path:
        prs.save(str(path))
    return prs


def _layout(prs, name):
    for lay in prs.slide_layouts:
        if lay.name == name:
            return lay
    raise KeyError(f"template has no layout named {name!r}; need {LAYOUTS}")


def _set_transition(slide, kind="fade"):
    sld = slide._element
    for old in sld.findall(qn("p:transition")):
        sld.remove(old)
    tr = etree.fromstring(f'<p:transition xmlns:p="{P_NS}" spd="med"><p:{kind}/></p:transition>')
    anchor = sld.find(qn("p:clrMapOvr"))
    (anchor if anchor is not None else sld.cSld).addnext(tr)


def _label(slide, text, theme, light=False):
    t = THEMES.get(theme, THEMES["blue"])
    tb = slide.shapes.add_textbox(Inches(1.2 if light else 0.8), Inches(1.2 if light else 0.4), Inches(6), Inches(0.5))
    tb.name = "BBP Label"
    tb.text_frame.text = text.upper()
    f = tb.text_frame.paragraphs[0].font
    f.size, f.bold = Pt(16), True
    f.color.rgb = _rgb(t["mid"] if light else t["accent"])


def outline_to_pptx(o: Outline, out: str | Path, template: str | Path | None = None, theme: str | None = None,
                    slide_transitions: bool = True) -> Path:
    theme = theme or o.theme
    prs = Presentation(str(template)) if template else build_template(theme)
    cp = prs.core_properties
    cp.title, cp.subject, cp.category = o.name, o.audience, "Beyond Bullet Points"
    cp.keywords = f"bbp;theme={theme}"
    cp.comments = o.footer
    cp.author = o.heading  # keeps <h1> for round-trip

    def add(layout, headline, notes, label=None, light=False, sub=None):
        s = prs.slides.add_slide(_layout(prs, layout))
        s.shapes.title.text = strip_md(headline).replace("\n", " ") if layout not in ("Resolution",) else strip_md(headline)
        if sub is not None and len(s.placeholders) > 1:
            s.placeholders[1].text = sub
        if label:
            _label(s, label, theme, light)
        s.notes_slide.notes_text_frame.text = notes
        return s

    acts = o.acts + [""] * (3 - len(o.acts))
    add("Title", o.headline, o.headline + ("\n" + o.subtitle if o.subtitle else ""), sub=o.subtitle)
    s = add("Act Header", acts[0], acts[0])
    slide_transitions and _set_transition(s, "push")
    add("Setting", o.setting, o.setting)
    add("Role", o.role, o.role)
    add("PointA", o.point_a, o.point_a)
    add("PointB", o.point_b, o.point_b)
    add("CallToAction", o.call_to_action, o.call_to_action)

    def transition(n, text):
        s = add("Transition", text, text, label=f"Transition {n}", light=True)
        slide_transitions and _set_transition(s, "fade")

    tr = o.transitions
    if tr:
        transition(1, tr[0])
    s = add("Act Header", acts[1], acts[1])
    slide_transitions and _set_transition(s, "push")
    for i, k in enumerate(o.key_ideas):
        if i > 0 and i < len(tr):
            transition(i + 1, tr[i])
        add("KeyPoint", k.headline, k.headline, label=f"Key Idea {i + 1}")
        for j, e in enumerate(k.explanations):
            add("Explanation", e.text, e.text, label=f"Explanation {i + 1}.{j + 1}")
            for d in e.details:
                add("Detail", d, d)
    for t_i in range(max(len(o.key_ideas), 1), len(tr)):
        transition(t_i + 1, tr[t_i])
    s = add("Act Header", acts[2], acts[2])
    slide_transitions and _set_transition(s, "push")
    for lab, txt in (("Challenge", o.challenge), ("Action", o.action), ("Outcome", o.outcome)):
        first = txt.split("\n")[0] if txt else lab
        add("Resolution", first, txt, label=lab)
    add("Closing", o.closing, o.closing)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(out))
    return out


def _slide_text(slide):
    notes = ""
    if slide.has_notes_slide:
        notes = norm(slide.notes_slide.notes_text_frame.text)
    if notes:
        return notes
    try:
        return norm(slide.shapes.title.text)
    except AttributeError:
        return ""


def _bbp_label(slide):
    for shp in slide.shapes:
        if shp.has_text_frame and shp.name == "BBP Label":
            return shp.text_frame.text.strip().lower()
    return ""


def _guess_layout(slide):
    """Fallback for hand-edited decks whose layouts were renamed."""
    name = slide.slide_layout.name
    if name in LAYOUTS:
        return name
    lab = _bbp_label(slide)
    for k, v in (("transition", "Transition"), ("key idea", "KeyPoint"), ("explanation", "Explanation"),
                 ("challenge", "Resolution"), ("action", "Resolution"), ("outcome", "Resolution")):
        if lab.startswith(k):
            return v
    return "Detail"


def pptx_to_outline(path: str | Path):
    """Return (Outline, extra_images) where extra_images maps md section keys to [(filename, bytes)]."""
    prs = Presentation(str(path))
    cp = prs.core_properties
    o = Outline(acts=[], heading=cp.author or "Beyond Bullet Points Outline", name=cp.title or Path(path).stem,
                audience=cp.subject or "", footer=norm(cp.comments or ""))
    for kw in (cp.keywords or "").split(";"):
        if kw.startswith("theme="):
            o.theme = kw[6:]
    images: dict[str, list] = {}
    ki = ex = None
    res = ["challenge", "action", "outcome"]
    res_i = 0
    key = "title"
    for n, slide in enumerate(prs.slides, start=1):
        lay = _guess_layout(slide)
        txt = _slide_text(slide)
        if lay == "Title":
            first, _, rest = txt.partition("\n")
            o.headline, o.subtitle = first, rest.strip()
            key = "title"
        elif lay == "Act Header":
            o.acts.append(txt)
            key = f"act-{len(o.acts)}"
        elif lay in ("Setting", "Role", "PointA", "PointB", "CallToAction"):
            f = {"Setting": "setting", "Role": "role", "PointA": "point_a", "PointB": "point_b",
                 "CallToAction": "call_to_action"}[lay]
            setattr(o, f, txt)
            key = f.replace("_", "-")
        elif lay == "Transition":
            o.transitions.append(txt)
            key = f"transition-{len(o.transitions)}"
        elif lay == "KeyPoint":
            ki = KeyIdea(txt)
            o.key_ideas.append(ki)
            ex = None
            key = f"key-{len(o.key_ideas)}"
        elif lay == "Explanation" and ki is not None:
            ex = Explanation(txt)
            ki.explanations.append(ex)
            key = f"exp-{len(o.key_ideas)}-{len(ki.explanations)}"
        elif lay == "Detail" and ex is not None:
            ex.details.append(txt)
            key = f"det-{len(o.key_ideas)}-{len(ki.explanations)}-{len(ex.details)}"
        elif lay == "Resolution":
            lab = _bbp_label(slide)
            if lab in ("challenge", "action", "outcome"):
                field = lab
            elif res_i < 3:
                field = res[res_i]
                res_i += 1
            else:
                field = None
            if field:
                setattr(o, field, txt)
                key = field
        elif lay == "Closing":
            o.closing = txt
            key = "closing"
        for k_img, shp in enumerate(s for s in slide.shapes if s.shape_type == MSO_SHAPE_TYPE.PICTURE):
            images.setdefault(key, []).append((f"slide-{n:02d}-img-{k_img + 1}.{shp.image.ext}", shp.image.blob))
    if not o.acts:
        o.acts = Outline().acts
    return o, images
