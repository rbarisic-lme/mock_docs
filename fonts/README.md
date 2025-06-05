# Font Directory

This directory is for custom font files (.ttf, .otf) that you want to use in your PDF templates.

## How to add fonts:

1. **Download font files** (`.ttf` or `.otf` format)
2. **Place them in this folder** (`fonts/`)
3. **Use the font name in your templates**

## Supported font formats:

- `.ttf` (TrueType fonts)
- `.otf` (OpenType fonts)

## Font name mapping:

The system will automatically try to find fonts using these patterns:

- `timesnewroman` → looks for `times.ttf`, `Times New Roman.ttf`, `TimesNewRoman.ttf`
- `arial` → looks for `arial.ttf`, `Arial.ttf`
- `calibri` → looks for `calibri.ttf`, `Calibri.ttf`
- `verdana` → looks for `verdana.ttf`, `Verdana.ttf`

## Search order:

1. **Local fonts/** folder (this directory) - **highest priority**
2. System fonts (Windows: C:/Windows/Fonts/, macOS: /System/Library/Fonts/, Linux: /usr/share/fonts/)
3. Fallback fonts (arial, calibri, helvetica)
4. PIL default font (last resort)

## Example:

If you want to use Times New Roman:

1. Download `times.ttf` or `Times New Roman.ttf`
2. Place it in this `fonts/` folder
3. In your template config, use: `"font": "timesnewroman"`

## Popular free fonts you can download:

- **Liberation Fonts** (Times, Arial, Courier alternatives): https://github.com/liberationfonts/liberation-fonts
- **Google Fonts**: https://fonts.google.com/
- **Font Squirrel**: https://www.fontsquirrel.com/

## Note:

Make sure you have the proper license for any fonts you use, especially for commercial projects!
