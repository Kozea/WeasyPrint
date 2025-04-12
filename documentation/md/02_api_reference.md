# WeasyPrint API Reference

This document provides comprehensive API documentation for WeasyPrint version 65.0.

## Core Classes

### HTML

The primary entry point for loading and rendering HTML documents.

```python
from weasyprint import HTML

# Basic usage
HTML('document.html').write_pdf('output.pdf')

# From a string
HTML(string='<h1>Hello World</h1>').write_pdf('output.pdf')

# From a URL
HTML(url='https://example.com').write_pdf('output.pdf')
```

#### Constructor Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| guess | Any | Parameter that WeasyPrint will try to identify as a filename, URL or file object | None |
| filename | str\|pathlib.Path | A filename, relative or absolute | None |
| url | str | An absolute, fully qualified URL | None |
| file_obj | file object | Any object with a read method | None |
| string | str | A string of HTML source | None |
| encoding | str | Force the source character encoding | None |
| base_url | str\|pathlib.Path | Base used to resolve relative URLs | None |
| url_fetcher | callable | Function to fetch external resources | default_url_fetcher |
| media_type | str | Media type to use for @media | 'print' |

**Note:** Exactly one of `guess`, `filename`, `url`, `file_obj`, or `string` must be provided.

#### Methods

##### render

Lay out and paginate the document, but do not export it.

```python
document = HTML('document.html').render()
```

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| font_config | FontConfiguration | Font configuration for @font-face rules | None |
| counter_style | CounterStyle | Dictionary for @counter-style rules | None |
| options | dict | Rendering options (extends DEFAULT_OPTIONS) | {} |

**Returns:** A `Document` object providing access to pages and metadata.

##### write_pdf

Render the document to a PDF file.

```python
# Write to file
HTML('document.html').write_pdf('output.pdf')

# Get PDF as bytes
pdf_bytes = HTML('document.html').write_pdf()
```

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | str\|pathlib.Path\|file object | Output filename or file object, or None to return bytes | None |
| zoom | float | Zoom factor in PDF units per CSS units | 1 |
| finisher | callable | Function for post-processing the PDF | None |
| font_config | FontConfiguration | Font configuration for @font-face rules | None |
| counter_style | CounterStyle | Dictionary for @counter-style rules | None |
| options | dict | Rendering options (extends DEFAULT_OPTIONS) | {} |

**Returns:** The PDF as bytes if target is None, otherwise None.

### CSS

Represents a CSS stylesheet to be applied to an HTML document.

```python
from weasyprint import HTML, CSS

html = HTML('document.html')
css = CSS('style.css')
html.write_pdf('output.pdf', stylesheets=[css])

# From a string
css = CSS(string='@page { size: A3 landscape; margin: 1cm }')
```

#### Constructor Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| guess | Any | Parameter that WeasyPrint will try to identify as a filename, URL or file object | None |
| filename | str | A filename, relative or absolute | None |
| url | str | An absolute, fully qualified URL | None |
| file_obj | file object | Any object with a read method | None |
| string | str | A string of CSS source | None |
| encoding | str | Force the source character encoding | None |
| base_url | str | Base used to resolve relative URLs | None |
| url_fetcher | callable | Function to fetch external resources | default_url_fetcher |
| media_type | str | Media type to use for @media | 'print' |
| font_config | FontConfiguration | Font configuration for @font-face rules | None |
| counter_style | dict | Dictionary storing @counter-style rules | None |

**Note:** Exactly one of `guess`, `filename`, `url`, `file_obj`, or `string` must be provided.

### Document

Represents a rendered document, created by `HTML.render()`.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| pages | list | List of Page objects |
| metadata | DocumentMetadata | Metadata associated with the document |

#### Methods

##### write_pdf

Render the document to a PDF file.

```python
document = HTML('document.html').render()
document.write_pdf('output.pdf')
```

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| target | str\|pathlib.Path\|file object | Output filename or file object, or None to return bytes | None |
| zoom | float | Zoom factor in PDF units per CSS units | 1 |
| finisher | callable | Function for post-processing the PDF | None |

**Returns:** The PDF as bytes if target is None, otherwise None.

### Page

Represents a single page in a rendered document.

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| width | float | Page width in CSS pixels |
| height | float | Page height in CSS pixels |
| bleed | dict | Bleed area with top, right, bottom, left keys |
| blocks | list | Page's blocks of boxes |
| bookmarks | list | Bookmarks for the page |
| links | list | Links for the page |
| anchors | dict | Anchors for the page |

### Attachment

Represents a file attachment for a PDF document.

```python
from weasyprint import HTML, Attachment

html = HTML('document.html')
attachment = Attachment('data.json', description='Data file')
html.write_pdf('output.pdf', attachments=[attachment])
```

#### Constructor Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| guess | Any | Parameter that WeasyPrint will try to identify as a filename, URL or file object | None |
| filename | str | A filename, relative or absolute | None |
| url | str | An absolute, fully qualified URL | None |
| file_obj | file object | Any object with a read method | None |
| string | str | A string content | None |
| base_url | str | Base used to resolve relative URLs | None |
| url_fetcher | callable | Function to fetch external resources | default_url_fetcher |
| name | str | Name of the attachment | None |
| description | str | Description of the attachment | None |
| created | datetime.datetime | Creation date and time | Current time |
| modified | datetime.datetime | Modification date and time | Current time |
| relationship | str | Relationship between attachment and PDF | 'Unspecified' |

### FontConfiguration

Configuration for fonts to be used in the document.

```python
from weasyprint import HTML, FontConfiguration

font_config = FontConfiguration()
HTML('document.html').write_pdf('output.pdf', font_config=font_config)
```

#### Methods

##### add_font_face

Add a @font-face rule.

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| descriptors | dict | Font descriptors | - |
| url_fetcher | callable | Function to fetch external resources | None |

### CounterStyle

Manages the definition and use of custom counter styles.

```python
from weasyprint import HTML, CounterStyle

counter_style = CounterStyle()
counter_style.add_counters({
    'custom': {
        'system': 'extends decimal',
        'prefix': '§',
        'suffix': '.'
    }
})
HTML('document.html').write_pdf('output.pdf', counter_style=counter_style)
```

#### Methods

##### add_counters

Add counter style rules.

| Parameter | Type | Description |
|-----------|------|-------------|
| counter_style_dict | dict | Dictionary of counter style rules |

## Functions

### default_url_fetcher

Default function for fetching URLs for resources.

```python
from weasyprint import default_url_fetcher, HTML

def my_url_fetcher(url):
    if url.startswith('myapp://'):
        # Handle custom URL scheme
        return {'string': '<h1>Custom content</h1>', 'mime_type': 'text/html'}
    return default_url_fetcher(url)

HTML('document.html', url_fetcher=my_url_fetcher).write_pdf('output.pdf')
```

| Parameter | Type | Description |
|-----------|------|-------------|
| url | str | The URL to fetch |

**Returns:** Dict with 'string' or 'file_obj' and metadata.

## Constants

### DEFAULT_OPTIONS

Default values for command-line and Python API options.

| Option | Default | Description |
|--------|---------|-------------|
| stylesheets | None | List of user stylesheets |
| media_type | 'print' | Media type for @media |
| attachments | None | List of file attachments |
| pdf_identifier | None | Bytestring used as PDF file identifier |
| pdf_variant | None | PDF variant name |
| pdf_version | None | PDF version number |
| pdf_forms | None | Whether to include PDF forms |
| uncompressed_pdf | False | Whether to compress PDF content |
| custom_metadata | False | Whether to store HTML metadata in PDF |
| presentational_hints | False | Whether to follow HTML presentational hints |
| srgb | False | Whether to include sRGB color profile |
| optimize_images | False | Whether to optimize embedded images |
| jpeg_quality | None | JPEG quality (0-95) |
| dpi | None | Maximum resolution for embedded images |
| full_fonts | False | Whether to embed unmodified font files |
| hinting | False | Whether to keep hinting in embedded fonts |
| cache | None | Dictionary or folder path for caching images |

### VERSION

WeasyPrint version string (e.g., "65.0").

## Common Usage Patterns

### Basic HTML to PDF conversion

```python
from weasyprint import HTML
HTML('document.html').write_pdf('document.pdf')
```

### HTML to PDF with custom CSS

```python
from weasyprint import HTML, CSS
html = HTML('document.html')
css = CSS('style.css')
html.write_pdf('document.pdf', stylesheets=[css])
```

### HTML string to PDF

```python
from weasyprint import HTML
HTML(string='<h1>Hello World</h1>').write_pdf('document.pdf')
```

### Custom document dimensions

```python
from weasyprint import HTML, CSS
html = HTML('document.html')
css = CSS(string='@page { size: A3 landscape; margin: 1cm }')
html.write_pdf('document.pdf', stylesheets=[css])
```

### Generate document with attachments

```python
from weasyprint import HTML, Attachment
html = HTML('document.html')
attachment = Attachment('data.json', description='Data file')
html.write_pdf('document.pdf', attachments=[attachment])
```