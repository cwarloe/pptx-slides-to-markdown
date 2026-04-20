import sys
import os
from urllib.parse import quote
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

DEFAULT_IMAGE_WIDTH_PX = 500


def safe_relpath_for_markdown(*parts):
    return "/".join(quote(part) for part in parts)


def extract_pptx_to_markdown_and_images(pptx_path, output_folder, image_width_px=DEFAULT_IMAGE_WIDTH_PX):
    pptx_path = os.path.normpath(pptx_path)
    output_folder = os.path.normpath(output_folder)

    presentation = Presentation(pptx_path)
    base_filename = os.path.splitext(os.path.basename(pptx_path))[0]

    markdown_content = []
    images_folder = os.path.join(output_folder, "images", base_filename)
    os.makedirs(images_folder, exist_ok=True)

    for slide_number, slide in enumerate(presentation.slides, start=1):
        title_text = ""
        title_shape = None

        for shape in slide.shapes:
            shape_name = getattr(shape, "name", "")
            text = getattr(shape, "text", "") or ""
            if shape_name.startswith("Title") and text.strip():
                title_text = text.strip()
                title_shape = shape
                break

        if not title_text:
            try:
                if slide.shapes.title and slide.shapes.title.text:
                    title_text = slide.shapes.title.text.strip()
                    title_shape = slide.shapes.title
            except Exception:
                pass

        if title_text:
            markdown_content.append(f"# Slide {slide_number} - {title_text}\n\n")
        else:
            markdown_content.append(f"# Slide {slide_number}\n\n")

        for shape in slide.shapes:
            if title_shape is not None and shape == title_shape:
                continue

            text = getattr(shape, "text", None)
            if text and text.strip():
                markdown_content.append(f"- {text.strip()}\n")

        if slide.has_notes_slide:
            try:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()
                if notes_text:
                    markdown_content.append("\n**Notes:**\n")
                    markdown_content.append(f"{notes_text}\n")
            except Exception:
                pass

        image_count = 0
        for shape in slide.shapes:
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    image = shape.image
                    image_ext = image.ext or "png"
                    image_filename = f"slide_{slide_number}_img_{image_count}.{image_ext}"
                    image_path = os.path.join(images_folder, image_filename)

                    with open(image_path, "wb") as img_file:
                        img_file.write(image.blob)

                    relative_image_path = safe_relpath_for_markdown(
                        "images", base_filename, image_filename
                    )

                    markdown_content.append(
                        f'\n<img src="{relative_image_path}" '
                        f'alt="Slide {slide_number} Image {image_count}" '
                        f'width="{image_width_px}" />\n'
                    )
                    image_count += 1
                except Exception as exc:
                    print(f"Warning: could not extract image from slide {slide_number}: {exc}")

        markdown_content.append("\n")

    output_md_path = os.path.join(output_folder, f"{base_filename}.md")
    with open(output_md_path, "w", encoding="utf-8") as file:
        file.write("".join(markdown_content))

    print(f"Markdown file created at: {output_md_path}")


def process_folder(input_folder, output_folder, image_width_px=DEFAULT_IMAGE_WIDTH_PX):
    input_folder = os.path.abspath(os.path.normpath(input_folder))
    output_folder = os.path.abspath(os.path.normpath(output_folder))

    if not os.path.isdir(input_folder):
        raise FileNotFoundError(f"Input folder not found: {input_folder}")

    os.makedirs(output_folder, exist_ok=True)

    pptx_files = sorted(
        filename for filename in os.listdir(input_folder)
        if filename.lower().endswith(".pptx")
    )

    if not pptx_files:
        print(f"No .pptx files found in: {input_folder}")
        return

    for filename in pptx_files:
        pptx_path = os.path.join(input_folder, filename)
        print(f"Processing: {pptx_path}")
        extract_pptx_to_markdown_and_images(
            pptx_path,
            output_folder,
            image_width_px=image_width_px
        )


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        print(
            'Usage: python extract_pptx_to_markdown_images_v3.py '
            '"<input_folder>" "<output_folder>" [image_width_px]'
        )
        sys.exit(1)

    input_folder = sys.argv[1]
    output_folder = sys.argv[2]

    if len(sys.argv) == 4:
        try:
            image_width_px = int(sys.argv[3])
        except ValueError:
            print("image_width_px must be an integer, for example: 500")
            sys.exit(1)
    else:
        image_width_px = DEFAULT_IMAGE_WIDTH_PX

    process_folder(input_folder, output_folder, image_width_px=image_width_px)
