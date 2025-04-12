# CSS Support in WeasyPrint

WeasyPrint provides extensive support for CSS specifications, enabling sophisticated document styling and layout. This document details the supported CSS features and their implementation status.

## CSS 2.1 Features

**Status: Well supported with limitations**

### Supported
- Most selectors and properties
- Box model
- Positioning
- Display types
- Tables
- Generated content
- Paged media

### Unsupported
- `::first-line` pseudo-element
- `visibility: collapse` on tables
- Minimum and maximum height on table-related boxes
- Right-to-left or bi-directional text
- System colors and system fonts

### Notes
- Passes the Acid2 Test
- Most features relevant to print media are supported

## CSS Selectors

### Selectors Level 3
**Status: Well supported**

#### Supported
- Type selectors (e.g., `h1`)
- Universal selector (`*`)
- Attribute selectors (e.g., `[attr=value]`)
- Class selectors (`.class`)
- ID selectors (`#id`)
- Pseudo-classes (`:first-child`, `:nth-child`, etc.)
- Pseudo-elements (`::before`, `::after`)
- Combinators (`>`, `+`, `~`)

#### Unsupported
- Interactive pseudo-classes (`:hover`, `:active`, `:focus`, `:target`, `:visited`)

#### Notes
- Interactive pseudo-classes are accepted as valid but never match anything since PDF is not interactive

### Selectors Level 4
**Status: Partially supported**

#### Supported
- Most Level 4 selectors

#### Unsupported
- `:dir` pseudo-class
- Input pseudo-classes (`:valid`, `:invalid`, etc.)
- Column selector (`||`, `:nth-col()`, `:nth-last-col()`)

## CSS Text Module

### CSS Text Module Level 3
**Status: Partially supported**

#### Supported
- `overflow-wrap` property
- `word-break: break-all`
- `text-transform: full-width`
- `text-align` properties and values
- `text-align-last`
- `text-justify`
- `tab-size`
- Hyphenation properties (`hyphens`, `hyphenate-character`, etc.)

#### Unsupported
- `line-break` property
- `text-align: match-parent`
- `text-indent`
- `hanging-punctuation`

#### Notes
- Automatic hyphenation requires `lang` HTML attribute set to a language supported by Pyphen

## CSS Fonts Module

### CSS Fonts Module Level 3
**Status: Well supported**

#### Supported
- `font-size`, `font-stretch`, `font-style`, `font-weight`
- `font-kerning`
- `font-variant-*` properties
- `font-feature-settings`
- `font-language-override`
- `@font-face` rule

#### Unsupported
- `@font-feature-values` rule
- `font-variant-alternates` values other than `normal` and `historical-forms`

#### Notes
- `font-family` string is given to Pango for font matching

## CSS Paged Media

### CSS Paged Media Module Level 3
**Status: Well supported**

#### Supported
- `@page` rule
- `:left`, `:right`, `:first`, `:blank` page selectors
- Page margin boxes
- Page-based counters
- `page` `size`, `bleed`, `marks` properties
- Named pages

#### Notes
- Some limitations with page-based counters

### CSS Generated Content for Paged Media Module
**Status: Partially supported**

#### Supported
- Page selectors (`:nth`)
- Running elements
- Footnotes
- `footnote-marker` and `footnote-call` pseudo-elements
- `footnote-display` property
- `footnote-policy` property

#### Unsupported
- `start` parameter of `element()`
- `compact` value for `footnote-display`

## CSS Generated Content

### CSS Generated Content Module Level 3
**Status: Partially supported**

#### Supported
- Named strings (`string-set`)
- Cross-references (`target-counter`, `target-text`)
- PDF bookmarks (`bookmark-level`, `bookmark-label`, `bookmark-state`)
- Leaders (`leader()`)

#### Unsupported
- Quotes (`content: *-quote`)

## CSS Color Module

### CSS Color Module Level 3
**Status: Well supported**

#### Supported
- Color keywords
- `#rgb`, `#rrggbb` syntax
- `rgb()`, `rgba()` syntax
- `hsl()`, `hsla()` syntax
- Opacity and alpha compositing

#### Unsupported
- Deprecated System Colors

## CSS Transforms

### CSS Transforms Module Level 1
**Status: Partially supported**

#### Supported
- `transform` and `transform-origin` properties
- 2D transformations (`matrix`, `rotate`, `translate`, `translateX`, `translateY`, `scale`, `scaleX`, `scaleY`, `skew`, `skewX`, `skewY`)

#### Unsupported
- `transform-style`, `perspective`, `perspective-origin`, `backface-visibility`
- 3D transformations

## CSS Backgrounds and Borders

### CSS Backgrounds and Borders Module Level 3
**Status: Well supported**

#### Supported
- Multiple background layers
- `background-*` properties
- Rounded corners (`border-radius`)
- Border images (`border-image-*`)

#### Unsupported
- Box shadows (`box-shadow`)

#### Notes
- Box shadow support exists in a git branch but not released

## CSS Image Values and Replaced Content

### CSS Image Values and Replaced Content Module Level 3/4
**Status: Partially supported**

#### Supported
- `linear-gradient()`
- `radial-gradient()`
- `repeating-radial-gradient()`
- `url()` notation for images
- `object-fit` and `object-position`
- `image-resolution` (except `from-image` and `snap` values)
- `image-rendering`
- `image-orientation`

#### Unsupported
- `image()` notation for background images

## CSS Layout Features

### CSS Box Sizing Module Level 3
**Status: Partially supported**

#### Supported
- `box-sizing` property

#### Unsupported
- `min-content`, `max-content`, and `fit-content()` sizing values

### CSS Overflow Module Level 3
**Status: Partially supported**

#### Supported
- `overflow` property (as defined in CSS2)
- `text-overflow`
- `block-ellipsis`
- `line-clamp`
- `max-lines`
- `continue` property

#### Unsupported
- `overflow-x`, `overflow-y`
- `overflow-clip-margin`
- `overflow-inline`, `overflow-block`

### CSS Values and Units Module Level 3
**Status: Well supported**

#### Supported
- `initial` and `inherit` keywords
- Quoted strings and URLs
- Numeric data types
- Font-related lengths (`em`, `ex`, `ch`, `rem`)
- Absolute lengths (`cm`, `mm`, `q`, `in`, `pt`, `pc`, `px`)
- Angles (`rad`, `grad`, `turn`, `deg`)
- Resolutions (`dpi`, `dpcm`, `dppx`)
- `attr()` function in `content` and `string-set`

#### Unsupported
- `unset` keyword
- `calc()` function
- Viewport-percentage lengths (`vw`, `vh`, `vmin`, `vmax`)

### CSS Multi-column Layout Module
**Status: Partially supported**

#### Supported
- `column-width` and `column-count` properties
- `columns` shorthand
- `column-gap`, `column-rule-*` properties
- `column-rule` shorthand
- `break-before`, `break-after`, `break-inside`
- `column-span` for direct children
- `column-fill` with balancing algorithm

#### Unsupported
- Constrained height columns
- Some column break cases
- Complex pagination and overflow

#### Notes
- Simple multi-column layouts are supported, but complex cases may have issues

### CSS Fragmentation Module Level 3/4
**Status: Partially supported**

#### Supported
- `break-before`, `break-after`, `break-inside` for pages
- `page-break-*` aliases from CSS2
- `orphans` and `widows` properties
- `box-decoration-break` property
- `margin-break` property

#### Unsupported
- `break-*` properties for columns and regions

#### Notes
- With `box-decoration-break`, backgrounds are always repeated and not extended through the whole box with 'slice' value

### CSS Custom Properties
**Status: Supported**

#### Supported
- Custom properties (`--*`)
- `var()` notation

### CSS Text Decoration Module Level 3/4
**Status: Partially supported**

#### Supported
- `text-decoration-line`, `text-decoration-style`, `text-decoration-color`
- `text-decoration-thickness`, `text-underline-offset`
- `text-decoration` shorthand

#### Unsupported
- `text-underline-position`
- `text-emphasis-*`
- `text-shadow`

### CSS Flexible Box Layout Module Level 1
**Status: Supported with limitations**

#### Supported
- `flex-*` properties
- `align-*` properties
- `justify-*` properties
- `order` property
- `flex` and `flex-flow` shorthands

#### Notes
- Works for simple use cases but not deeply tested

### CSS Grid Layout Module Level 2
**Status: Supported with limitations**

#### Supported
- `display: grid`
- `grid-auto-*`, `grid-template-*` and other `grid-*` properties
- `grid` and `grid-*` shorthands
- `fr` unit
- Line names and grid areas
- Auto rows and columns
- `z-index`
- `repeat(X, *)`
- `minmax()`
- `align-*` and `justify-*` properties
- `gap` and `*-gap` properties
- Dense auto flow
- `order`
- Margins, borders, padding on grid elements
- Fragmentation between rows

#### Unsupported
- `display: inline-grid`
- Auto content size for grid containers
- `grid-auto-flow: column`
- Subgrids
- `repeat(auto-fill, *)` and `repeat(auto-fit, *)`
- Auto margins for grid items
- `span` with line names
- `span` for flexible tracks
- `safe` and `unsafe` alignments
- Baseline alignment
- Grid items with intrinsic size (images)
- Distribute space beyond limits
- Grid items larger than grid containers
- `min-width`, `max-width`, `min-height`, `max-height` on grid items
- Complex `min-content` and `max-content` cases
- Absolutely positioned and floating grid items
- Fragmentation in rows

#### Notes
- Works for simple cases but has numerous limitations for complex layouts

### CSS Basic User Interface Module Level 3/4
**Status: Partially supported**

#### Supported
- `outline-width`, `outline-style`, `outline-color` properties
- `outline` shorthand
- `outline-offset` property
- `appearance` property for PDF form fields

#### Unsupported
- `resize`, `cursor`, `caret-*` and `nav-*` properties
- `accent-color` property

#### Notes
- `appearance: auto` displays form fields as PDF form fields for text inputs, check boxes, text areas, and select only

## Edge Cases and Testing Guidelines

When working with WeasyPrint's CSS support, consider these edge cases:

1. **Unsupported Features**: Always check if your CSS relies on unsupported features (like box-shadow or 3D transforms).

2. **Interactive Elements**: Avoid relying on interactive pseudo-classes as they won't match in PDF output.

3. **Complex Layouts**: Test thoroughly when using advanced features like Grid, Flexbox, or Multi-column layout with complex content.

4. **Font Usage**: Ensure fonts are available on the system or properly embedded to avoid unexpected substitutions.

5. **Image Handling**: Be careful with SVG files that use complex or unsupported features.

6. **Page Breaks**: Test documents with multiple pages to ensure proper page breaking and headers/footers.

7. **Hyphenation**: To enable hyphenation, set the `lang` attribute on HTML elements and use `hyphens: auto`.

8. **Right-to-Left Text**: Consider the limited RTL support when creating documents in languages like Arabic or Hebrew.

9. **Form Fields**: When using form fields, test with `appearance: auto` and verify the behavior.

10. **Viewport Units**: Replace `vw`, `vh`, `vmin`, `vmax` units with absolute units for consistent rendering.

## Recommended CSS Patterns

For optimal results with WeasyPrint, consider these recommended patterns:

1. **Page Setup**:
   ```css
   @page {
     size: A4;
     margin: 2cm;
     @top-center { content: "Header Text"; }
     @bottom-center { content: "Page " counter(page); }
   }
   ```

2. **Custom Page Sizes**:
   ```css
   @page {
     size: 210mm 297mm; /* Custom size */
   }
   ```

3. **Page Breaks**:
   ```css
   h1 {
     page-break-before: always;
   }
   ```

4. **Multi-column Layout**:
   ```css
   .content {
     column-count: 2;
     column-gap: 20px;
     column-rule: 1px solid #ccc;
   }
   ```

5. **Footnotes**:
   ```css
   .footnote {
     float: footnote;
   }
   .footnote::footnote-marker {
     content: counter(footnote);
   }
   ```

6. **Leaders (for TOC)**:
   ```css
   .toc-entry::after {
     content: leader(dotted) " " target-counter(attr(href), page);
   }
   ```

7. **Running Headers**:
   ```css
   h1 { string-set: chapter content(); }
   @page {
     @top-center { content: string(chapter); }
   }
   ```

8. **PDF Bookmarks**:
   ```css
   h1 {
     bookmark-level: 1;
     bookmark-label: content();
   }
   ```