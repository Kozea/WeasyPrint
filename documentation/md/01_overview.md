# WeasyPrint Overview

**Version:** 65.0  
**License:** BSD

## What is WeasyPrint?

WeasyPrint is a visual rendering engine for HTML and CSS that can export to PDF. It turns simple HTML pages into gorgeous statistical reports, invoices, tickets, and other high-quality documents. Unlike browser engines like WebKit or Gecko, WeasyPrint has its own CSS layout engine written in Python, designed for pagination, and optimized to be hackable.

## Key Features

### HTML Support
- Most HTML5 elements via CSS styling
- Embedded images (raster and SVG)
- HTML forms (via appearance: auto)
- Links and anchors

### CSS Support
- CSS 2.1 (nearly complete)
- Most CSS3 modules including:
  - Selectors Level 3 & 4
  - Paged Media
  - Generated Content
  - 2D Transforms
  - Flexbox and Grid layout (with limitations)
  - Custom Properties
  - Multi-column Layout

### Paged Media
- Page size and margins
- Page selectors and named pages
- Headers and footers (margin boxes)
- Page breaks and control
- Footnotes

### PDF Features
- Hyperlinks (internal and external)
- Bookmarks/outlines
- Attachments
- Form fields
- Embedded fonts
- PDF/A and PDF/UA support
- Metadata

### Text & Image Support
- Unicode support
- Hyphenation
- Font variations and features
- PNG, JPEG, GIF, and other raster formats
- SVG as vectors (not rasterized)
- Image sizing, cropping, and resolution control

## System Requirements

- **Python Version:** 3.9+
- **Tested Platforms:** CPython, PyPy

### Python Dependencies
- pydyf (PDF generation)
- tinyhtml5 (HTML parsing)
- tinycss2 (CSS parsing)
- cssselect2 (CSS selectors)
- Pyphen (Hyphenation)
- Pillow (Image handling)
- fonttools (Font management)

### System Dependencies
- Pango (Text layout)
- HarfBuzz (Text shaping)
- FreeType (Font support)
- Fontconfig (Font discovery)
- Cairo (Graphics)

## Integration Methods

### Python API
```python
from weasyprint import HTML
HTML('document.html').write_pdf('document.pdf')
```

### Command Line
```bash
weasyprint input.html output.pdf
```

### Web Service
```python
@app.route('/pdf')
def pdf():
    html = render_template('document.html')
    pdf = HTML(string=html).write_pdf()
    return pdf, {'Content-Type': 'application/pdf'}
```

## Limitations

- No JavaScript support
- Limited interactive features (hover states not meaningful in PDF)
- Some CSS features not implemented (box-shadow, 3D transforms)
- Performance issues with very large documents
- Limited support for right-to-left text

## Resources

- **Repository:** [https://github.com/Kozea/WeasyPrint](https://github.com/Kozea/WeasyPrint)
- **Documentation:** [https://doc.courtbouillon.org/weasyprint](https://doc.courtbouillon.org/weasyprint)
- **Website:** [https://weasyprint.org](https://weasyprint.org)

## Contributors

- **Original Creator:** Kozea (https://kozea.fr/)
- **Maintenance:** CourtBouillon (https://www.courtbouillon.org/)