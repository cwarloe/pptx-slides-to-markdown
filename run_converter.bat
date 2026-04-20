@echo off
set INPUT_FOLDER=sample-input
set OUTPUT_FOLDER=sample-output
set IMAGE_WIDTH=500

python extract_pptx_to_markdown_images_v3.py "%INPUT_FOLDER%" "%OUTPUT_FOLDER%" %IMAGE_WIDTH%
pause
