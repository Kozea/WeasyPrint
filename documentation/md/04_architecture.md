# WeasyPrint Architecture

This document provides a detailed overview of WeasyPrint's rendering pipeline, internal architecture, and module organization.

## Rendering Pipeline

WeasyPrint follows a structured rendering pipeline to transform HTML and CSS into PDF documents:

### 1. HTML Parsing

**Module:** `tinyhtml5`  
**Input:** HTML content (file, URL, string)  
**Output:** DOM tree

The first stage parses HTML content into a DOM tree structure that can be processed by CSS selectors. WeasyPrint uses the `tinyhtml5` parser for this purpose.

**Key Components:**
- `HTML.__init__`: Entry point for HTML parsing
- `_find_base_url`: Determines the base URL for resolving relative URLs

### 2. CSS Parsing

**Module:** `tinycss2`  
**Input:** CSS content (file, URL, string)  
**Output:** Parsed CSS rules

This stage parses CSS stylesheets and processes CSS rules. WeasyPrint uses `tinycss2` for CSS parsing.

**Key Components:**
- `CSS.__init__`: Entry point for CSS parsing
- `preprocess_stylesheet`: Processes CSS at-rules and properties, handling `@media`, `@font-face`, etc.

### 3. Style Computation

**Module:** `weasyprint.css`  
**Input:** DOM tree and CSS rules  
**Output:** DOM tree with computed styles

This stage computes the final style for each element in the document, applying the CSS cascade, inheritance, and resolving variables.

**Key Components:**
- `computed_values.compute_value`: Computes values for CSS properties
- `cssselect2.Matcher`: Matches CSS selectors against DOM elements

### 4. Box Generation

**Module:** `weasyprint.formatting_structure`  
**Input:** DOM tree with computed styles  
**Output:** Box tree

This stage transforms the DOM tree into a tree of boxes based on the display property and other styling. These boxes represent the visual rendering of the document.

**Key Components:**
- `build.build_formatting_structure`: Creates boxes for each element
- `boxes.BoxFactory`: Factory that creates appropriate box types

### 5. Layout Calculation

**Module:** `weasyprint.layout`  
**Input:** Box tree  
**Output:** Box tree with dimensions and positions

This stage calculates dimensions and positions for all boxes, implementing different layout models (block, inline, flex, grid, table).

**Key Components:**
- `layout_document`: Coordinates layout of the entire document
- `block_box_layout`: Layout for block-level boxes
- `inline_line_box_layout`: Layout for inline-level boxes
- `flex_layout`: Layout for flex containers
- `grid_layout`: Layout for grid containers
- `table_layout`: Layout for tables

### 6. Pagination

**Module:** `weasyprint.layout.page`  
**Input:** Box tree with dimensions and positions  
**Output:** List of pages with content

This stage splits content across multiple pages based on page dimensions, content flow, and explicit page break properties.

**Key Components:**
- `make_page`: Creates new pages with proper dimensions and margins
- `page_break_required`: Determines if a page break is needed
- `split_box_with_page_break`: Splits boxes across pages

### 7. Footnote Processing

**Module:** `weasyprint.layout`  
**Input:** List of pages with content  
**Output:** List of pages with content and footnotes

This stage collects footnotes and positions them at the bottom of each page, adjusting page content as needed.

**Key Components:**
- `layout_footnote`: Lays out footnote content

### 8. Background Processing

**Module:** `weasyprint.layout.background`  
**Input:** List of pages with content  
**Output:** List of pages with backgrounds

This stage processes backgrounds for all boxes, handling positioning, tiling, and clipping.

**Key Components:**
- `layout_backgrounds`: Lays out backgrounds for boxes

### 9. Stacking Context Creation

**Module:** `weasyprint.stacking`  
**Input:** List of pages with content and backgrounds  
**Output:** List of pages with stacking contexts

This stage determines the order in which elements are painted, implementing CSS stacking contexts.

**Key Components:**
- `create_stacking_context`: Creates stacking contexts based on CSS properties

### 10. Drawing/Rendering

**Module:** `weasyprint.draw`  
**Input:** List of pages with stacking contexts  
**Output:** Rendering instructions

This stage transforms the layout information into drawing commands for the PDF.

**Key Components:**
- `draw_page`: Draws a page to a PDF context
- `stacking.paint_stacking_context`: Paints elements in the proper order

### 11. PDF Generation

**Module:** `weasyprint.pdf`  
**Input:** Rendering instructions  
**Output:** PDF document

This final stage creates the PDF document with all content, hyperlinks, bookmarks, attachments, and metadata.

**Key Components:**
- `Document.write_pdf`: Entry point for PDF generation
- `write_pdf_metadata`: Writes metadata to the PDF
- `anchors.create_anchors`: Creates hyperlinks and bookmarks

## Module Organization

### Core Modules

#### weasyprint.css
- **Purpose:** CSS parsing, validation, and property processing
- **Submodules:**
  - `computed_values`: Computes CSS values based on inheritance and cascade
  - `counters`: Implements CSS counters
  - `properties`: Defines CSS properties and their values
  - `targets`: Implements target-* dynamic values
  - `validation`: Validates CSS declarations

#### weasyprint.layout
- **Purpose:** Layout engines for different display types
- **Submodules:**
  - `absolute`: Layout for absolutely positioned elements
  - `background`: Background layout for CSS boxes
  - `block`: Layout for blocks and block-like boxes
  - `flex`: Layout for CSS Flexbox
  - `float`: Layout for CSS floats
  - `grid`: Layout for CSS Grid
  - `inline`: Layout for inline-level boxes
  - `page`: Layout for pages and pagination
  - `table`: Layout for tables

#### weasyprint.formatting_structure
- **Purpose:** Box model implementation
- **Submodules:**
  - `boxes`: Defines the box model classes
  - `build`: Builds the formatting structure from the document tree

#### weasyprint.pdf
- **Purpose:** PDF generation
- **Submodules:**
  - `anchors`: Manages PDF anchors, links, and bookmarks
  - `fonts`: Embeds fonts in PDF documents
  - `metadata`: Handles metadata in the PDF document
  - `pdfa`: PDF/A support (archival PDF)
  - `pdfua`: PDF/UA support (accessible PDF)
  - `stream`: Stream PDF generation

#### weasyprint.text
- **Purpose:** Text handling and font management
- **Submodules:**
  - `constants`: Text-related constants
  - `ffi`: Foreign function interface for text libraries
  - `fonts`: Font handling and configuration
  - `line_break`: Line breaking algorithm

#### weasyprint.draw
- **Purpose:** Drawing and rendering
- **Submodules:**
  - `border`: Border drawing
  - `color`: Color handling
  - `stack`: Drawing stack management
  - `text`: Text drawing

#### weasyprint.svg
- **Purpose:** SVG rendering
- **Submodules:**
  - `bounding_box`: SVG bounding box calculations
  - `css`: SVG CSS handling
  - `defs`: SVG definitions
  - `images`: SVG image handling
  - `path`: SVG path rendering
  - `shapes`: SVG shape rendering
  - `text`: SVG text rendering
  - `utils`: SVG utilities

### Supporting Modules

#### weasyprint.urls
- **Purpose:** URL handling and resource fetching
- **Key Functions:**
  - `default_url_fetcher`: Default function for fetching resources
  - `fetch`: Fetches a resource from a URL
  - `path2url`: Converts a filesystem path to a URL

#### weasyprint.logger
- **Purpose:** Logging configuration
- **Key Components:**
  - `LOGGER`: Main logger for errors and warnings
  - `PROGRESS_LOGGER`: Logger for progress information

#### weasyprint.images
- **Purpose:** Image handling and processing
- **Key Functions:**
  - Image loading and optimization

## Key Data Structures

### HTML
Represents an HTML document parsed by tinyhtml5.
- `base_url`: Base URL for resolving relative URLs
- `wrapper_element`: CSS wrapper for the HTML root element
- `etree_element`: HTML root element

### CSS
Represents a CSS stylesheet parsed by tinycss2.
- `base_url`: Base URL for resolving relative URLs
- `matcher`: CSS selector matcher
- `page_rules`: List of @page rules

### Box
Base class for all CSS boxes.
- `element_tag`: HTML tag name
- `style`: Computed style dictionary
- `children`: Child boxes
- `width`: Box width
- `height`: Box height
- `position_x`: X position
- `position_y`: Y position

Box subclasses include:
- `BlockBox`: Block-level box
- `InlineBox`: Inline-level box
- `LineBox`: Line box in an inline formatting context
- `TableBox`: Table
- `FlexBox`: Flex container
- `GridBox`: Grid container

### Page
Represents a page in the document.
- `width`: Page width
- `height`: Page height
- `margin_boxes`: Page margin boxes
- `blocks`: Block boxes in the page
- `background`: Page background
- `bookmarks`: Bookmarks for the page
- `links`: Links in the page
- `anchors`: Named anchors in the page

### Document
Represents the rendered document.
- `pages`: List of pages
- `metadata`: Document metadata
- `bookmarks`: Document bookmarks
- `links`: Document links
- `attachments`: Document attachments

## Optimization Strategies

WeasyPrint employs several optimization strategies to improve performance:

1. **Box caching:** Caches box layouts to avoid recomputing
2. **Image caching:** Caches images to avoid repeated loading and processing
3. **Font subsetting:** Embeds only used glyphs from fonts
4. **Image optimization:** Optimizes images for size and quality

## Integration Points

WeasyPrint provides several integration points for extending or customizing behavior:

### URL Fetcher
The `url_fetcher` parameter in `HTML` and `CSS` constructors allows customizing resource fetching.

```python
def custom_url_fetcher(url):
    if url.startswith('myapp://'):
        # Custom handling
        return {'string': '<h1>Content</h1>', 'mime_type': 'text/html'}
    # Fall back to default behavior
    return default_url_fetcher(url)

HTML('document.html', url_fetcher=custom_url_fetcher).write_pdf('output.pdf')
```

### Font Configuration
The `FontConfiguration` class allows customizing font handling.

```python
font_config = FontConfiguration()
font_config.add_font_face({
    'font-family': 'Custom Font',
    'src': 'url(fonts/custom.ttf)',
})
HTML('document.html').write_pdf('output.pdf', font_config=font_config)
```

### PDF Finisher
The `finisher` parameter in `write_pdf` allows post-processing the PDF.

```python
def pdf_finisher(document, pdf):
    # Add watermark or other custom processing
    pass

HTML('document.html').write_pdf('output.pdf', finisher=pdf_finisher)
```

## Component Interactions

The following diagram illustrates the interactions between major components:

```
HTML Input
   ↓
HTML Parsing (tinyhtml5)
   ↓
DOM Tree
   ↓     ← CSS Stylesheets
Style Computation (cssselect2, weasyprint.css)
   ↓
DOM Tree with Computed Styles
   ↓
Box Generation (weasyprint.formatting_structure)
   ↓
Box Tree
   ↓
Layout Calculation (weasyprint.layout)
   ↓
Box Tree with Dimensions and Positions
   ↓
Pagination (weasyprint.layout.page)
   ↓
Pages with Content
   ↓
Background Processing (weasyprint.layout.background)
   ↓
Stacking Context Creation (weasyprint.stacking)
   ↓
Drawing/Rendering (weasyprint.draw)
   ↓
PDF Generation (weasyprint.pdf, pydyf)
   ↓
PDF Output
```

## Architectural Decisions

Several key architectural decisions shape WeasyPrint's design:

1. **Pure Python Implementation:** The core layout engine is written in Python, focusing on correctness over raw performance.

2. **Modular Design:** Clear separation between stages of rendering pipeline, allowing for focused development and testing.

3. **External Libraries:** Uses specialized libraries (tinyhtml5, tinycss2, cssselect2) for parsing and selecting, rather than reimplementing these features.

4. **Stateless Processing:** Most components are designed to be stateless, improving maintainability and testing.

5. **Progressive Rendering:** The pipeline processes documents in stages, allowing for more efficient memory usage.

6. **Error Resilience:** Many errors are logged but don't stop processing, allowing for partial rendering even with problematic content.

## Performance Considerations

When working with WeasyPrint at scale, consider these performance aspects:

1. **Document Size:** Very large documents may require significant memory and processing time.

2. **Complex Layouts:** Grid and Flexbox layouts, especially with dynamic sizing, can be computationally expensive.

3. **Font Handling:** Font embedding and text shaping can be performance bottlenecks with many fonts or complex text.

4. **Image Processing:** Large or numerous images can impact performance, especially without caching.

5. **CSS Complexity:** Complex selectors and excessive rule specificity can slow down style computation.

6. **External Resources:** Fetching many external resources can introduce latency.

By understanding WeasyPrint's architecture and pipeline, developers can better design documents that render efficiently and debug issues when they arise.