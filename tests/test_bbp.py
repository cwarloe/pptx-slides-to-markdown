"""Round-trip tests over real docs/bbp-outline.html files from Charles's repos."""
from pathlib import Path
import filecmp
import zipfile

import pytest
from pptx import Presentation

from bbp.html_io import parse_html, render_html, _cell_md
from bbp.md_io import parse_markdown, render_markdown
from bbp.model import Outline, norm
from bbp.pptx_io import LAYOUTS, build_template, outline_to_pptx, pptx_to_outline

FIXTURES = sorted((Path(__file__).parent / "fixtures").glob("*.html"))


def dirs_equal(a: Path, b: Path) -> bool:
    cmp = filecmp.dircmp(a, b)
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(dirs_equal(a / d, b / d) for d in cmp.common_dirs)


@pytest.mark.parametrize("fx", FIXTURES, ids=lambda p: p.stem)
def test_parse_shape(fx):
    o = parse_html(fx.read_text(encoding="utf-8"))
    assert o.headline and o.setting and o.role and o.point_a and o.point_b and o.call_to_action
    assert len(o.transitions) == 3
    assert len(o.key_ideas) == 3
    assert all(len(k.explanations) == 3 and all(len(e.details) == 3 for e in k.explanations) for k in o.key_ideas)
    assert o.closing and o.footer and len(o.acts) == 3


@pytest.mark.parametrize("fx", FIXTURES, ids=lambda p: p.stem)
def test_outline_pptx_md_roundtrip(fx, tmp_path):
    o = parse_html(fx.read_text(encoding="utf-8"))
    deck = outline_to_pptx(o, tmp_path / "deck.pptx")
    o2, imgs = pptx_to_outline(deck)
    assert o2 == o
    render_markdown(o, tmp_path / "a" / "x.md")
    render_markdown(o2, tmp_path / "b" / "x.md", imgs)
    assert (tmp_path / "a" / "x.md").read_text() == (tmp_path / "b" / "x.md").read_text()
    assert dirs_equal(tmp_path / "a", tmp_path / "b")


@pytest.mark.parametrize("fx", FIXTURES, ids=lambda p: p.stem)
def test_md_and_html_roundtrip(fx, tmp_path):
    o = parse_html(fx.read_text(encoding="utf-8"))
    md = render_markdown(o, tmp_path / "x.md")
    assert parse_markdown(md.read_text()) == o
    assert parse_html(render_html(o)) == o
    assert (tmp_path / "x_images" / "transition-1.png").exists()
    assert "> **Transition 2:**" in md.read_text()


def test_deck_uses_bbp_layouts_and_transitions(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    deck = outline_to_pptx(o, tmp_path / "d.pptx")
    prs = Presentation(str(deck))
    assert [l.name for l in prs.slide_layouts] == LAYOUTS
    names = [s.slide_layout.name for s in prs.slides]
    assert names.count("Transition") == 3 and names.count("KeyPoint") == 3 and names.count("Detail") == 27
    assert names[:7] == ["Title", "Act Header", "Setting", "Role", "PointA", "PointB", "CallToAction"]
    for s in prs.slides:
        assert s.notes_slide.notes_text_frame.text.strip()
    xml = zipfile.ZipFile(deck).read("ppt/slides/slide8.xml").decode()
    assert "<p:transition" in xml and "<p:fade" in xml


def test_hand_edited_deck_picture_is_extracted(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    deck = outline_to_pptx(o, tmp_path / "d.pptx")
    render_markdown(o, tmp_path / "ref" / "x.md")  # makes a png to embed
    prs = Presentation(str(deck))
    key_slide = next(s for s in prs.slides if s.slide_layout.name == "KeyPoint")
    key_slide.shapes.add_picture(str(tmp_path / "ref" / "x_images" / "transition-1.png"), 0, 0, 914400, 514350)
    key_slide.notes_slide.notes_text_frame.text = ""  # edited deck without notes: fall back to title
    prs.save(str(tmp_path / "edited.pptx"))
    o2, imgs = pptx_to_outline(tmp_path / "edited.pptx")
    assert o2.key_ideas[0].headline == o.key_ideas[0].headline
    md = render_markdown(o2, tmp_path / "out" / "e.md", imgs).read_text()
    assert "e_images/slide-" in md
    assert list((tmp_path / "out" / "e_images").glob("slide-*-img-1.png"))


def test_template_file(tmp_path):
    build_template("green", tmp_path / "m.pptx")
    assert [l.name for l in Presentation(str(tmp_path / "m.pptx")).slide_layouts] == LAYOUTS


def test_multiline_key_idea_explanation_and_detail_survive_markdown(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.key_ideas[0].headline = "Idea first\nIdea second"
    o.key_ideas[0].explanations[0].text = "Explain first\nExplain second"
    o.key_ideas[0].explanations[0].details[0] = "Detail first\nDetail second"
    md = render_markdown(o, tmp_path / "x.md")
    o2 = parse_markdown(md.read_text())
    assert o2.key_ideas[0].headline == "Idea first\nIdea second"
    assert o2.key_ideas[0].explanations[0].text == "Explain first\nExplain second"
    assert o2.key_ideas[0].explanations[0].details[0] == "Detail first\nDetail second"


def test_renamed_resolution_layout_keeps_challenge_action_outcome(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    deck = outline_to_pptx(o, tmp_path / "d.pptx")
    prs = Presentation(str(deck))
    for lay in prs.slide_layouts:
        if lay.name == "Resolution":
            lay._element.cSld.set("name", "Renamed Resolution")
    prs.save(str(tmp_path / "renamed.pptx"))
    o2, _ = pptx_to_outline(tmp_path / "renamed.pptx")
    assert o2.challenge == o.challenge
    assert o2.action == o.action
    assert o2.outcome == o.outcome
    last_details = o2.key_ideas[-1].explanations[-1].details
    assert o.challenge not in last_details
    assert o.action not in last_details
    assert o.outcome not in last_details


def _rename_layouts(src, dest, mapping):
    prs = Presentation(str(src))
    for lay in prs.slide_layouts:
        if lay.name in mapping:
            lay._element.cSld.set("name", mapping[lay.name])
    prs.save(str(dest))


def test_empty_resolution_fields_stay_empty_through_pptx(tmp_path):
    o = Outline(headline="Only a title")
    o2, _ = pptx_to_outline(outline_to_pptx(o, tmp_path / "bare.pptx"))
    assert (o2.challenge, o2.action, o2.outcome) == ("", "", "")
    assert o2.headline == "Only a title"


def test_hr_in_field_does_not_become_footer_when_footer_empty(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.footer = ""
    o.setting = "Before the break\n---\nAfter the break"
    o2 = parse_markdown(render_markdown(o, tmp_path / "hr.md").read_text())
    assert o2.setting == "Before the break\n---\nAfter the break"
    assert o2.footer == ""
    assert o2.role == o.role
    assert o2.closing == o.closing


def test_renamed_unlabeled_layouts_keep_fields(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.acts = ["ACT 1: CUSTOM SETUP", "ACT 2: CUSTOM DEVELOP", "ACT 3: CUSTOM RESOLUTION"]
    deck = outline_to_pptx(o, tmp_path / "d.pptx")

    _rename_layouts(deck, tmp_path / "close.pptx", {"Closing": "The End"})
    o2, _ = pptx_to_outline(tmp_path / "close.pptx")
    assert o2.closing == o.closing
    assert o.closing not in o2.key_ideas[-1].explanations[-1].details
    assert len(o2.key_ideas[-1].explanations[-1].details) == len(o.key_ideas[-1].explanations[-1].details)

    _rename_layouts(deck, tmp_path / "act.pptx", {"Act Header": "Section"})
    o3, _ = pptx_to_outline(tmp_path / "act.pptx")
    assert o3.acts == o.acts
    assert "ACT 3: CUSTOM RESOLUTION" not in o3.key_ideas[-1].explanations[-1].details

    _rename_layouts(deck, tmp_path / "act1.pptx", {
        "Title": "Cover", "Setting": "XSetting", "Role": "XRole",
        "PointA": "XPointA", "PointB": "XPointB", "CallToAction": "XCTA",
    })
    o4, _ = pptx_to_outline(tmp_path / "act1.pptx")
    assert o4.headline == o.headline
    assert o4.subtitle == o.subtitle
    assert o4.setting == o.setting
    assert o4.role == o.role
    assert o4.point_a == o.point_a
    assert o4.point_b == o.point_b
    assert o4.call_to_action == o.call_to_action

    _rename_layouts(deck, tmp_path / "all.pptx", {n: f"Renamed {n}" for n in LAYOUTS})
    o5, _ = pptx_to_outline(tmp_path / "all.pptx")
    assert o5.headline == o.headline
    assert o5.subtitle == o.subtitle
    assert o5.setting == o.setting
    assert o5.role == o.role
    assert o5.point_a == o.point_a
    assert o5.point_b == o.point_b
    assert o5.call_to_action == o.call_to_action
    assert o5.acts == o.acts
    assert o5.challenge == o.challenge
    assert o5.action == o.action
    assert o5.outcome == o.outcome
    assert o5.closing == o.closing
    assert o5.transitions == o.transitions
    assert o5.key_ideas == o.key_ideas


def test_markdown_reserved_line_prefixes_roundtrip(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    orig_headline = o.headline
    o.setting = "Intro line\n# this looks like a heading\nMore setting"
    o2 = parse_markdown(render_markdown(o, tmp_path / "h.md").read_text())
    assert o2.setting == "Intro line\n# this looks like a heading\nMore setting"
    assert o2.headline == orig_headline

    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.setting = "See this\n- item\nAfter"
    assert parse_markdown(render_markdown(o, tmp_path / "b.md").read_text()).setting == "See this\n- item\nAfter"

    o.setting = "See this\n> quoted\nAfter"
    assert parse_markdown(render_markdown(o, tmp_path / "q.md").read_text()).setting == "See this\n> quoted\nAfter"

    o.setting = "See this\n![alt](foo.png)\nAfter"
    assert parse_markdown(render_markdown(o, tmp_path / "i.md").read_text()).setting == "See this\n![alt](foo.png)\nAfter"

    o.setting = "See this\n### Secret\nAfter"
    assert parse_markdown(render_markdown(o, tmp_path / "s.md").read_text()).setting == "See this\n### Secret\nAfter"

    o.key_ideas[0].headline = "Idea first\n- looks like a bullet"
    o.key_ideas[0].explanations[0].text = "Explain first\n- looks like a bullet"
    o3 = parse_markdown(render_markdown(o, tmp_path / "k.md").read_text())
    assert o3.key_ideas[0].headline == "Idea first\n- looks like a bullet"
    assert o3.key_ideas[0].explanations[0].text == "Explain first\n- looks like a bullet"
    assert o3.key_ideas[0].explanations[0].details == o.key_ideas[0].explanations[0].details


def test_indented_setting_lines_survive_markdown(tmp_path):
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.setting = "  hello  \n  world  \n"
    o2 = parse_markdown(render_markdown(o, tmp_path / "ind.md").read_text())
    assert o2.setting == norm(o.setting) == "hello\nworld"


def test_html_title_keeps_inner_bold():
    o = parse_html(FIXTURES[0].read_text(encoding="utf-8"))
    o.headline = "The **title**"
    o2 = parse_html(render_html(o))
    assert o2.headline == "The **title**"


def test_html_list_items_are_separated():
    from bs4 import BeautifulSoup
    td = BeautifulSoup(
        "<td><ul><li>one</li><li>two<ul><li>nested</li></ul></li></ul></td>",
        "html.parser",
    ).td
    text = _cell_md(td)
    assert "one" in text and "two" in text and "nested" in text
    assert text != "onetwonested"
    assert "\n" in text
