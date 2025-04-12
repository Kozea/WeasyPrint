# WeasyPrint Documentation Guide

This document provides an overview of the WeasyPrint documentation structure and how to use it effectively.

## Documentation Organization

The WeasyPrint documentation is organized into a structured hierarchy of information, designed to serve different user needs:

### Tiered Documentation Approach

1. **Tier 1: Overview** - High-level introduction for new users
2. **Tier 2: API Reference** - Detailed API information for developers
3. **Tier 3: Feature Documentation** - Comprehensive feature details and edge cases
4. **Tier 4: Architecture and Internals** - Internal structure and technical details
5. **Tier 5: Diagnostics** - Troubleshooting and failure recovery information

### Document Types

The documentation consists of two formats:

1. **JSON Files** - Structured, machine-readable documentation in `/documentation/*.json`
2. **Markdown Files** - Human-readable documentation in `/documentation/md/*.md`

## Available Documentation

### JSON Documentation

| Filename | Description | Primary Use |
|----------|-------------|-------------|
| `metadata.json` | Library overview, features, requirements | Entry point to all documentation |
| `api.json` | Public API classes, methods, parameters | Integration reference |
| `css_module.json` | CSS module structure and internals | Internal architecture reference |
| `layout_module.json` | Layout engine documentation | Internal architecture reference |
| `pdf_module.json` | PDF generation functionality | Internal architecture reference |
| `css_features.json` | Supported CSS features | Feature reference |
| `rendering_pipeline.json` | Document processing pipeline | Technical documentation |
| `failure_analysis.json` | Failure modes and diagnostics | Troubleshooting reference |
| `README.json` | Documentation about the documentation | Meta-documentation |

### Markdown Documentation

| Filename | Description | Content Source | Tier |
|----------|-------------|----------------|------|
| `00_index.md` | Documentation overview and navigation | `README.json` | Meta |
| `01_overview.md` | High-level introduction to WeasyPrint | `metadata.json` | 1 |
| `02_api_reference.md` | Public API documentation | `api.json` | 2 |
| `03_css_support.md` | CSS features and usage patterns | `css_features.json` | 3 |
| `04_architecture.md` | Technical architecture information | `rendering_pipeline.json`, `layout_module.json` | 4 |
| `05_failure_diagnostics.md` | Troubleshooting and recovery | `failure_analysis.json` | 5 |
| `06_pdf_module.md` | PDF generation details | `pdf_module.json` | 4 |
| `07_css_internals.md` | CSS module internal structure | `css_module.json` | 4 |
| `08_documentation_guide.md` | Documentation usage guidance | `README.json` | Meta |

### Enhancement Documentation

In addition to the core documentation, there are also enhancement proposals:

| Filename | Description | Location |
|----------|-------------|----------|
| `flex-enhancements.json` | Proposal for full Flexbox support | `/documentation/enhancements/` |

## How to Use This Documentation

### Finding Information

1. **New Users**: Start with `01_overview.md` to understand WeasyPrint's capabilities, installation requirements, and basic usage patterns.

2. **Developers Integrating WeasyPrint**: Refer to `02_api_reference.md` for detailed API documentation, including classes, methods, parameters, and usage examples.

3. **CSS Authors**: Use `03_css_support.md` to understand which CSS features are supported, their limitations, and recommended usage patterns for optimal results.

4. **Contributors and Technical Users**:
   - `04_architecture.md` - Understand the overall rendering pipeline and architecture
   - `06_pdf_module.md` - Learn about PDF generation capabilities and advanced options
   - `07_css_internals.md` - Explore the internal structure of the CSS processing module

5. **Troubleshooters**: When issues arise, consult `05_failure_diagnostics.md` for common failure modes, their causes, and recovery strategies.

### Documentation Navigation

The documentation is designed to be navigated in several ways:

1. **Sequential Reading**: Start with `00_index.md` and follow the numerical sequence for a comprehensive understanding.

2. **Topic-Based Access**: Go directly to the document that covers your area of interest.

3. **Cross-References**: Follow links between documents to explore related topics.

### Programmatic Access

The JSON documentation can be used programmatically:

```python
import json

# Load API documentation
with open('documentation/api.json', 'r') as f:
    api_docs = json.load(f)

# Extract information about a specific class
html_class = next(export for export in api_docs['main_exports'] 
                 if export['name'] == 'HTML')

# Use the information
print(f"HTML class description: {html_class['description']}")
```

This approach enables:
- Automated documentation generation
- Integration with development tools
- Custom documentation views based on specific needs

## Documentation Features

### Cross-References

The documentation includes cross-references between related topics. Look for links to other documents for more detailed information on specific subjects.

### Code Examples

Code examples are provided throughout the documentation to illustrate key concepts and usage patterns. These examples are designed to be copy-paste ready for quick implementation.

```python
# Example from API Reference
from weasyprint import HTML, CSS
html = HTML('document.html')
css = CSS('style.css')
html.write_pdf('output.pdf', stylesheets=[css])
```

### API Tables

API reference information is presented in tables for easy scanning, with details on:
- Parameters and their types
- Return values and types
- Default values and options

### Feature Matrices

CSS and other feature support is documented in detailed matrices showing:
- Support status (full, partial, unsupported)
- Limitations or notes
- Version information where applicable

### Failure Analysis

The failure diagnostics documentation provides structured information about common issues, including:
- Error symptoms
- Root causes
- Recovery strategies
- Prevention measures

## Documentation Maintenance

### Source of Truth

The JSON files are the source of truth for all documentation. The Markdown files are generated from these JSON files and should not be edited directly to maintain consistency.

### Generating Updated Documentation

To regenerate Markdown documentation from updated JSON files:

1. Use the Documentation Agent with access to the JSON files
2. Request generation of specific or all Markdown documents
3. Review the generated output for accuracy and consistency

### Contributing to Documentation

To contribute to the documentation:

1. Update the relevant JSON file(s) with new or corrected information
2. Regenerate the affected Markdown files
3. Submit your changes through the normal contribution process

### Enhancement Proposals

The `/documentation/enhancements/` directory contains JSON files documenting proposed enhancements to WeasyPrint. These follow a structured format describing:

- Current functionality
- Proposed changes
- Implementation strategy
- Benefits and challenges

## Documentation Versions

This documentation applies to WeasyPrint version 65.0. Different versions may have different features and API details. Always refer to documentation that matches your installed version.

## Additional Resources

- **GitHub Repository**: [https://github.com/Kozea/WeasyPrint](https://github.com/Kozea/WeasyPrint)
- **Official Documentation**: [https://doc.courtbouillon.org/weasyprint](https://doc.courtbouillon.org/weasyprint)
- **Website**: [https://weasyprint.org](https://weasyprint.org)
- **Support**: [https://www.courtbouillon.org](https://www.courtbouillon.org)

## Document Generation Metadata

- **Generation Date**: 2025-04-12
- **Documentation Tool**: Documentation Agent
- **Source Version**: WeasyPrint 65.0
- **License**: BSD