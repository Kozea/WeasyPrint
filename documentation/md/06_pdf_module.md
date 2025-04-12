# WeasyPrint PDF Module

This document describes the PDF generation functionality of WeasyPrint, which transforms rendered documents into PDF files.

## Overview

The PDF module (`weasyprint.pdf`) is responsible for creating PDF documents from the rendered document structure. It handles PDF-specific features like hyperlinks, bookmarks, metadata, fonts, and various PDF standards compliance.

WeasyPrint uses the `pydyf` library for low-level PDF generation, which enables it to create sophisticated PDF documents with a variety of features beyond basic content rendering.

## Key Exports

### Main Functions

| Function | Description | Parameters |
|----------|-------------|------------|
| `write_pdf_metadata` | Write metadata to a PDF file | `pdf`: pydyf.PDF object<br>`metadata`: dict with metadata to add |
| `draw_page` | Draw a Page object as a PDF page | `pdf`: pydyf.PDF object<br>`page`: Page object to draw<br>`scale`: float scale factor |

## Submodules

### anchors (`weasyprint.pdf.anchors`)

Manages PDF anchors, links, and bookmarks.

**Key Functions:**
- `create_anchors`: Creates all anchors in the PDF document, implementing internal and external hyperlinks, as well as document bookmarks/outlines.

### fonts (`weasyprint.pdf.fonts`)

Handles font embedding in PDF documents.

**Key Functions:**
- `embed_font`: Embeds a font in the PDF document, ensuring that text renders correctly regardless of fonts installed on the end user's system.

### metadata (`weasyprint.pdf.metadata`)

Handles document metadata like title, author, and keywords.

**Key Functions:**
- `add_metadata`: Adds metadata to a PDF document, including standard metadata fields like title, author, subject, keywords, and creation/modification dates.

### pdfa (`weasyprint.pdf.pdfa`)

Provides support for PDF/A, the archival format for long-term preservation.

**Key Functions:**
- `customize_pdf_document`: Modifies a PDF document to make it PDF/A compliant, adding necessary color profiles, metadata, and ensuring file structure follows the PDF/A standard.

### pdfua (`weasyprint.pdf.pdfua`)

Implements PDF/UA (Universal Accessibility) support for creating accessible documents.

**Key Functions:**
- `customize_pdf_document`: Makes a PDF document PDF/UA compliant by adding appropriate tags, structure, and metadata to ensure accessibility for users with disabilities.

### stream (`weasyprint.pdf.stream`)

Handles streaming PDF generation and resource embedding.

**Key Functions:**
- `get_image_from_uri`: Retrieves an image from a URI for embedding in the PDF
- `draw_image`: Draws an image in the PDF document

## PDF Features

WeasyPrint supports a wide range of PDF features:

### Document Metadata

**Description:** Add standard metadata like title, author, keywords  
**Related Module:** `metadata`  
**Usage Example:**
```python
from weasyprint import HTML
html = HTML('document.html')
html.write_pdf('output.pdf', attachments=None)  # metadata from HTML meta tags
```

### Hyperlinks

**Description:** Internal and external hyperlinks  
**Related Module:** `anchors`  
**Usage Example:**
```html
<!-- In your HTML -->
<a href="https://example.com">External link</a>
<a href="#section1">Internal link to an ID</a>
```

### Bookmarks

**Description:** PDF outlines/bookmarks for navigation  
**Related Module:** `anchors`  
**Usage Example:**
```css
/* In your CSS */
h1 { bookmark-level: 1; bookmark-label: content(); }
h2 { bookmark-level: 2; bookmark-label: content(); }
```

### Font Embedding

**Description:** Embed fonts in the PDF for consistent rendering  
**Related Module:** `fonts`  
**Usage Example:**
```css
/* In your CSS */
@font-face {
  font-family: 'CustomFont';
  src: url('path/to/font.ttf');
}
body { font-family: 'CustomFont', sans-serif; }
```

### Attachments

**Description:** Attach files to the PDF document  
**Related Module:** `stream`  
**Usage Example:**
```python
from weasyprint import HTML, Attachment
html = HTML('document.html')
attachment = Attachment('data.json', description='Data file')
html.write_pdf('output.pdf', attachments=[attachment])
```

### Form Fields

**Description:** Interactive form fields  
**Related Module:** `stream`  
**Usage Example:**
```css
/* In your CSS */
input, textarea, select { appearance: auto; }
```

### PDF/A Support

**Description:** Create PDF/A compliant documents for archiving  
**Related Module:** `pdfa`  
**Usage Example:**
```python
from weasyprint import HTML
html = HTML('document.html')
html.write_pdf('output.pdf', pdf_variant='pdf/a-3b')
```

### PDF/UA Support

**Description:** Create PDF/UA compliant documents for accessibility  
**Related Module:** `pdfua`  
**Usage Example:**
```python
from weasyprint import HTML
html = HTML('document.html')
html.write_pdf('output.pdf', pdf_variant='pdf/ua-1')
```

## Implementation Details

### PDF Generation Process

1. Create a `pydyf.PDF` object
2. For each page in the document:
   - Create a new PDF page
   - Draw all content (text, images, shapes)
   - Apply backgrounds and borders
3. Add document-level features (bookmarks, links, metadata)
4. Apply PDF variant customizations if needed (PDF/A, PDF/UA)
5. Write the PDF to the output target

### PDF Variants

| Variant | Description | Use Case |
|---------|-------------|----------|
| Standard | Normal PDF generation | General-purpose documents |
| PDF/A | Archival format ensuring long-term accessibility | Documents that need to be preserved for long periods |
| PDF/UA | Universal accessibility compliance | Documents that must be accessible to users with disabilities |

### Compression Options

PDF output can be compressed or uncompressed, controlled via the `uncompressed_pdf` option. Compression significantly reduces file size but may slightly increase generation time.

### Image Handling

- **Optimization:** Optional image optimization can reduce file size
- **Formats:** Supports JPEG, PNG, GIF, and SVG (as vectors)
- **Quality Control:** JPEG quality setting (0-95) for balancing size and quality

## Advanced Topics

### Custom PDF Finishers

WeasyPrint allows post-processing on the PDF through the finisher parameter:

```python
def custom_finisher(document, pdf):
    # Add custom watermark or other modifications
    pdf.add_information(Creator="Custom Application")

html.write_pdf('output.pdf', finisher=custom_finisher)
```

### PDF Encryption

While WeasyPrint doesn't directly support PDF encryption, you can use external libraries like PyPDF2 to encrypt the output:

```python
from weasyprint import HTML
from PyPDF2 import PdfReader, PdfWriter

# Generate the PDF
pdf_bytes = HTML('document.html').write_pdf()

# Encrypt using PyPDF2
reader = PdfReader(BytesIO(pdf_bytes))
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

writer.encrypt("user_password", "owner_password")

with open("encrypted_output.pdf", "wb") as f:
    writer.write(f)
```

### Optimizing PDF Size

For smaller PDF files, consider:

1. Use optimized images (enable with `optimize_images=True`)
2. Set appropriate JPEG quality (`jpeg_quality=75`)
3. Limit embedded fonts to used characters (`full_fonts=False`)
4. Set an appropriate DPI for raster images (`dpi=96`)

```python
html.write_pdf('output.pdf', 
              optimize_images=True,
              jpeg_quality=75,
              full_fonts=False,
              dpi=96)
```

## Common Issues and Solutions

### Font Embedding Problems

**Issue:** Fonts appear different in the PDF than in the browser  
**Solution:** Ensure fonts are properly installed or embedded via `@font-face`. Check font licensing if embedding is restricted.

### Large File Sizes

**Issue:** PDF files are too large  
**Solution:** 
- Use `optimize_images=True`
- Lower `jpeg_quality` 
- Simplify complex SVG graphics
- Avoid embedding full fonts with `full_fonts=False`

### Missing Links or Bookmarks

**Issue:** Hyperlinks or bookmarks don't work in the PDF  
**Solution:** Ensure proper HTML structure with IDs for internal links. For bookmarks, use CSS `bookmark-*` properties on appropriate headings.

### PDF/A or PDF/UA Validation Failures

**Issue:** Documents don't pass compliance validators  
**Solution:** 
- Ensure all fonts are embedded
- Add proper alt text for images
- Use semantic HTML structure
- Add document language metadata