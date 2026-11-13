# pptx-slides-to-markdown

> “Give me your tired, your poor, your huddled slide decks yearning to breathe free — in Markdown.”

Turn PowerPoint slide decks into Markdown with extracted images and Git-friendly structure, so training content can live, breathe, and improve in GitHub or GitLab.

## What this does

This tool helps convert `.pptx` slide decks into:

- Markdown files
- extracted image folders
- GitHub/GitLab-friendly relative image references

It is especially useful for:

- training content
- lesson plans
- instructor notes
- converting slide-based content into maintainable documentation

## Features

- pulls slide text into Markdown
- extracts slide images
- writes relative image links that render in Markdown viewers
- URL-encodes image paths for spaces in file names
- writes UTF-8 Markdown output
- supports batch conversion for all `.pptx` files in a folder
- uses HTML `<img>` tags so image width can be controlled

## Requirements

- Python 3.10+
- `python-pptx`

Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the script like this:

```bash
python extract_pptx_to_markdown_images_v3.py "C:\path\to\input folder" "C:\path\to\output folder"
```

Optional third argument for image width:

```bash
python extract_pptx_to_markdown_images_v3.py "C:\path\to\input folder" "C:\path\to\output folder" 500
```

## Windows quick start

You can also use the included batch file:

```bat
run_converter.bat
```

Edit the paths in that file first.

## Output structure

```text
output-folder/
├─ deck-name.md
└─ images/
   └─ deck-name/
      ├─ slide_1_img_0.png
      ├─ slide_2_img_0.png
      └─ ...
```

## Notes

- Keep the `images` folder next to the generated Markdown files.
- The script is designed for practical conversion, not perfect semantic reconstruction.
- Some decks may need a cleanup pass afterward if they use unusual layouts.

## Why this exists

PowerPoint is often where training content begins, but it is rarely where reusable documentation should end.

This project helps move content from slide decks into version-controlled Markdown so it can be reviewed, improved, reused, and published more easily.

## License

MIT

## Beyond Bullet Points (BBP) pipeline

The `bbp` package converts the Beyond Bullet Points outline (`docs/bbp-outline.html`,
the three-column `bbp-table` template) to and from PowerPoint and Markdown.

```bash
pip install -r requirements.txt

# outline -> PowerPoint on the BBP slide layouts
python -m bbp convert docs/bbp-outline.html --to pptx -o out/talk.pptx
#   --theme blue|green|orange|purple|gray   (defaults to the outline's body data-theme)
#   --template my-masters.pptx              (your own design; keep the layout names)
#   --no-slide-transitions                  (skip the fade/push XML transitions)

# outline -> Markdown + images folder (out/talk.md + out/talk_images/)
python -m bbp convert docs/bbp-outline.html --to md -o out/talk.md

# PowerPoint -> Markdown + images folder (layout names + speaker notes drive it)
python -m bbp convert out/talk.pptx --to md -o out/talk-from-deck.md

# Markdown -> outline HTML (round trip back to the table format)
python -m bbp convert out/talk.md --to html -o out/bbp-outline.html

# write the empty master/layout template to restyle by hand
python -m bbp template --theme blue -o bbp-masters.pptx
```

**Slide layouts** (the "pre-scripted masters"): `Title`, `Act Header`, `Setting`, `Role`,
`PointA`, `PointB`, `CallToAction`, `Transition`, `KeyPoint`, `Explanation`, `Detail`,
`Resolution`, `Closing`. Each slide carries a full-sentence headline in the title
placeholder, no bullets, and the source cell text in the speaker notes. Act 1 runs in BBP
order: Setting, Role, Point A, Point B, Call to Action. Each key idea runs Key Point (the 5-minute
version), then three Explanation slides (15 minutes), each followed by its Detail slides (45 minutes).

**Transitions** have their own `Transition` layout: a full-color slide with a
"TRANSITION N" label and the bridging sentence as the headline. Transition and act slides also
get real fade or push slide transitions. In Markdown, a transition is a marked block
(`> **Transition N:** ...`) with a rendered card image at `<name>_images/transition-N.png`.

**Parse-back** reads the layout names and notes. Hand-edited decks still work: if the notes
are empty, it falls back to the title text. If a layout was renamed, it uses the "BBP Label" text box.
Any pictures on slides are extracted into `<name>_images/slide-NN-img-K.ext` and linked under
their section.

Tests (`pip install -r requirements-dev.txt && python -m pytest -q`) use real outlines
from nine repos in `tests/fixtures/`. They check outline -> pptx -> md against outline -> md
(identical Markdown and images), md -> outline, and outline -> HTML -> outline.

The layouts only approximate Cliff Atkinson's BBP story template. His real PowerPoint
templates come with the book and are proprietary, so they are not copied here. Pass `--template`
to use your own design.
