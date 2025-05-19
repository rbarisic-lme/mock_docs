# PDF Template Visual Editor

A visual editor for creating and managing PDF document templates for automated document processing. This tool allows users to visually design templates by overlaying text, images, and shapes on top of PDF pages, making it easy to define generation zones for automation.

**Note:** This project is a work in progress (WIP). Contributions, feedback, and issues are welcome!

## Features

- Visual editing of PDF templates: add, move, resize text, images
- Multi-page PDF support
- Drag-and-drop interface with zoom and pan
- Save/load template configurations as JSON
- Image and text property editing (font, color, alignment, padding, etc.)
- Real-time preview of template overlays

## Prerequisites

- Python 3.8+
- [pip](https://pip.pypa.io/en/stable/)
- Windows 10+ (tested; other OS may work with minor changes)
- Tesseract 5.5.0 (https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.0)
  - with additional training tools for (e.g. german) language

## Installation

1. Clone the repository:
   ```sh
   git clone <your-repo-url>
   cd doc-templater
   ```
2. (Optional) Create and activate a virtual environment:
   ```sh
   python -m venv venv
   venv\Scripts\activate  # On Windows
   # Or: source venv/bin/activate  # On Linux/Mac
   ```
3. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Usage

1. Place your input PDFs in the `input_pdfs/` directory.
2. Run the template editor:
   ```sh
   python template_editor.py
   ```
3. Select a PDF, design your template visually, and save the configuration.
4. Template configurations are saved in the `configs/` directory as JSON files.
5. Run `doc_templater.py` to generate your batch templated pdfs.

## Directory Structure

- `app/template_editor/` – Main editor code (UI, event handling, rendering)
- `input_pdfs/` – Place your source PDFs here
- `input_img/` – Place images for use in templates
- `output_pdfs/` – (Optional) Output directory for generated PDFs
- `configs/` – Stores template configuration JSON files
- `temp_images/` – Temporary images for previews/thumbnails

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT License](LICENSE)
