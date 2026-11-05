"""Round-trip tests over real docs/bbp-outline.html files from Charles's repos."""
from pathlib import Path
import filecmp
import zipfile

import pytest
from pptx import Presentation

from bbp.html_io import parse_html, render_html
from bbp.md_io import parse_markdown, render_markdown
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
