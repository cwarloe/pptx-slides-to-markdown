"""bbp command line: python -m bbp convert IN --to pptx|md|html [-o OUT]."""
from __future__ import annotations

import argparse
from pathlib import Path

from .html_io import parse_html, render_html
from .md_io import parse_markdown, render_markdown
from .pptx_io import build_template, outline_to_pptx, pptx_to_outline


def load(path: Path):
    ext = path.suffix.lower()
    if ext in (".html", ".htm"):
        return parse_html(path.read_text(encoding="utf-8")), {}
    if ext == ".md":
        return parse_markdown(path.read_text(encoding="utf-8")), {}
    if ext == ".pptx":
        return pptx_to_outline(path)
    raise SystemExit(f"unsupported input: {path}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bbp", description="Beyond Bullet Points outline converter")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("convert", help="convert outline HTML / markdown / pptx")
    c.add_argument("input", type=Path)
    c.add_argument("--to", required=True, choices=["pptx", "md", "html"])
    c.add_argument("-o", "--out", type=Path, help="output file (default: out/<name>.<ext>)")
    c.add_argument("--template", type=Path, help="custom .pptx with the BBP layout names")
    c.add_argument("--theme", choices=["blue", "green", "orange", "purple", "gray"])
    c.add_argument("--no-slide-transitions", action="store_true")
    t = sub.add_parser("template", help="write the BBP master/layout template .pptx")
    t.add_argument("-o", "--out", type=Path, default=Path("bbp-masters.pptx"))
    t.add_argument("--theme", default="blue")
    a = ap.parse_args(argv)
    if a.cmd == "template":
        build_template(a.theme, a.out)
        print(a.out)
        return
    outline, images = load(a.input)
    stem = a.input.stem if a.input.stem not in ("bbp-outline",) else (a.input.parent.parent.name or "bbp-outline")
    out = a.out or Path("out") / f"{stem}.{a.to}"
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.to == "pptx":
        outline_to_pptx(outline, out, a.template, a.theme, not a.no_slide_transitions)
    elif a.to == "md":
        if a.theme:
            outline.theme = a.theme
        render_markdown(outline, out, images)
    else:
        out.write_text(render_html(outline), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
