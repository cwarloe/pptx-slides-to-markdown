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
