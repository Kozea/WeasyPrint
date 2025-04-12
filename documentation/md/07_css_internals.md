# WeasyPrint CSS Internals

This document provides an in-depth look at the internal structure and functionality of WeasyPrint's CSS processing module.

## Overview

The CSS module (`weasyprint.css`) is responsible for parsing, validating, and processing CSS stylesheets. It handles all aspects of CSS, from parsing using tinycss2 to computing final values for each element in the document.

## Module Structure

### Main Module (`weasyprint.css`)

The main CSS module provides the core functionality for processing CSS stylesheets.

**Key Exports:**

| Function | Description | Parameters |
|----------|-------------|------------|
| `preprocess_stylesheet` | Process a parsed CSS stylesheet | `media_type`: Media type for @media rules<br>`base_url`: Base URL for resolving relative URLs<br>`stylesheet`: A tinycss2 parsed stylesheet<br>`url_fetcher`: Function to fetch external resources<br>`matcher`: The CSS selector matcher<br>`page_rules`: List to fill with page rules<br>`font_config`: Font configuration<br>`counter_style`: Dictionary of counter style rules |

### Submodules

#### computed_values (`weasyprint.css.computed_values`)

Handles the computation of CSS values for properties based on inheritance and cascade.

**Key Exports:**
- `INITIAL_VALUES`: Dictionary of initial values for CSS properties
- `compute_value`: Function to get the computed value of a property on an element
- `resolve_var_function`: Function to resolve CSS variables in property values

#### counters (`weasyprint.css.counters`)

Implements CSS counters for automatic numbering.

**Key Exports:**
- `CounterStyle`: Class for managing counter styles
  - `add_counters`: Add counter style rules
  - `get_counter_style`: Get a counter style by name

#### properties (`weasyprint.css.properties`)

Defines CSS properties and their characteristics.

**Key Exports:**
- `PROPERTIES`: Dictionary mapping CSS property names to their definitions
- `SHORTHANDS`: Dictionary mapping shorthand CSS property names to their definitions

#### targets (`weasyprint.css.targets`)

Implements target-* dynamic values for cross-references.

**Key Exports:**
- `TargetCollector`: Class that collects target references needed by the target-* properties

#### validation (`weasyprint.css.validation`)

Handles validation and correction of CSS declarations and values.

**Submodules:**
- `descriptors`: Validates descriptors for @font-face and @counter-style
- `expanders`: Expands CSS shorthand properties into their component properties
- `properties`: Validates CSS property declarations

## CSS Processing Pipeline

The CSS processing in WeasyPrint follows these main steps:

1. **Parsing**: CSS text is parsed using tinycss2 into a token tree
2. **At-rule processing**: @media, @import, @font-face, and other at-rules are processed
3. **Property validation**: Property values are validated and normalized
4. **Selector matching**: CSS selectors are matched against DOM elements
5. **Cascade resolution**: Conflicting declarations are resolved using specificity and importance
6. **Inheritance**: Inheritable properties are passed down to child elements
7. **Variable resolution**: CSS variables (`--*` properties) are resolved
8. **Computed value calculation**: Final computed values are determined for each property

## Key Concepts

### CSS Selectors Matching

WeasyPrint uses cssselect2 for matching CSS selectors to HTML elements. This provides support for complex selectors including:

- Type selectors (`div`, `span`)
- Universal selector (`*`)
- Attribute selectors (`[attr]`, `[attr=value]`)
- Class selectors (`.class`)
- ID selectors (`#id`)
- Pseudo-classes (`:first-child`, `:nth-child`)
- Pseudo-elements (`::before`, `::after`)
- Combinators (`>`, `+`, `~`, descendant)

### Cascading

The cascade algorithm determines which CSS declarations take precedence when multiple rules match an element. Priority is determined by:

1. Importance (normal vs. `!important`)
2. Origin (user agent vs. author vs. user styles)
3. Specificity of selectors
4. Source order (last declaration wins)

### Inheritance

Some CSS properties automatically inherit from parent to child elements. WeasyPrint correctly implements inheritance, allowing properties like `color`, `font-family`, and `text-align` to flow down the document tree.

### CSS Variables (Custom Properties)

WeasyPrint supports CSS custom properties (variables) through the `var()` function:

```css
:root {
  --main-color: #06c;
}

h1 {
  color: var(--main-color);
}
```

The `resolve_var_function` handles the variable substitution process, including fallback values.

## Supported At-Rules

### @font-face

WeasyPrint supports `@font-face` for custom font definitions:

```css
@font-face {
  font-family: 'MyFont';
  src: url('myfont.woff2') format('woff2'),
       url('myfont.woff') format('woff');
  font-weight: normal;
  font-style: normal;
}
```

Fonts are processed by the `FontConfiguration` class and embedded in the final PDF.

### @media

Media queries allow applying CSS conditionally based on media type:

```css
@media print {
  /* Print-specific styles */
}

@media screen {
  /* Screen-specific styles (ignored in WeasyPrint by default) */
}
```

WeasyPrint uses `'print'` as the default media type.

### @page

The `@page` rule defines page-level properties:

```css
@page {
  size: A4;
  margin: 2cm;
}

@page :first {
  margin-top: 3cm;
}
```

Page rules are collected during preprocessing and applied during the pagination phase.

### @counter-style

Custom counter styles can be defined with `@counter-style`:

```css
@counter-style circled-decimal {
  system: fixed;
  symbols: ① ② ③ ④ ⑤ ⑥ ⑦ ⑧ ⑨ ⑩;
  suffix: " ";
}
```

Counter styles are processed by the `CounterStyle` class.

## CSS Feature Implementation

### Implementation Constraints

Some CSS features have implementation constraints in WeasyPrint:

1. **Pagination Context**: WeasyPrint operates in a pagination context, which affects how some properties work compared to browsers
2. **Static Nature**: Interactive features (`:hover`, `:active`) are not relevant in PDF outputs
3. **Object Model Limitations**: Some features may be limited by the underlying Pango text handling

### CSS Extensions

WeasyPrint implements some CSS extensions for print-specific functionality:

- **Bookmarks**: Properties like `bookmark-level` and `bookmark-label` control PDF bookmarks
- **Cross-references**: Functions like `target-counter()` and `target-text()` for document cross-references
- **Leaders**: The `leader()` function for creating leader lines in tables of contents

## Performance Considerations

### Stylesheet Optimization

For better performance with large documents:

1. **Selector Specificity**: Use simpler selectors where possible
2. **Variable Usage**: Limit excessive variable dependency chains
3. **Property Count**: Use shorthand properties where appropriate
4. **Media Queries**: Only include print-relevant styles

### Memory Usage

CSS processing can be memory-intensive with complex stylesheets. Consider:

1. **Stylesheet Size**: Split very large stylesheets
2. **Selector Complexity**: Avoid overly complex selectors
3. **At-rule Nesting**: Minimize deeply nested at-rules

## Debugging CSS Issues

### Common Problems

1. **Selector Not Matching**: Check specificity and rule order
2. **Unexpected Inheritance**: Check if properties are inheritable
3. **Variable Resolution**: Ensure variables are defined before use
4. **Media Type Mismatch**: Confirm media queries are for 'print'

### Diagnostic Approaches

1. **Simplified Test Case**: Create minimal examples to isolate issues
2. **Property Inspection**: Check computed values for specific elements
3. **Rule Tracing**: Add diagnostic CSS with visible effects to trace rule application

## Extending CSS Support

To extend CSS support in WeasyPrint:

1. **Property Definition**: Add property definitions in `properties.py`
2. **Initial Values**: Define initial values in `computed_values.py`
3. **Validation Logic**: Implement validation in `validation/properties.py`
4. **Computed Value Calculation**: Add compute functions in `computed_values.py`
5. **Layout Integration**: Connect property values to layout algorithms