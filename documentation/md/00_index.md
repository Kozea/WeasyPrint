# WeasyPrint Documentation

**Version:** 65.0

This documentation provides comprehensive information about the WeasyPrint HTML-to-PDF conversion library.

## Table of Contents

1. [Overview](01_overview.md) - High-level introduction to WeasyPrint
2. [API Reference](02_api_reference.md) - Detailed API documentation
3. [CSS Support](03_css_support.md) - Supported CSS features and usage patterns
4. [Architecture](04_architecture.md) - Technical architecture and rendering pipeline
5. [Failure Diagnostics](05_failure_diagnostics.md) - Troubleshooting and failure recovery
6. [PDF Module](06_pdf_module.md) - PDF generation capabilities and options
7. [CSS Internals](07_css_internals.md) - Internal structure of the CSS processing module
8. [Documentation Guide](08_documentation_guide.md) - How to use this documentation effectively

## Enhancement Proposals

- [CSS Flexbox Full Compliance](enhancements/flex-enhancements.md) - Proposal for enhancing WeasyPrint's Flexbox support

## Documentation Tiers

This documentation is organized into five tiers of increasing technical detail:

### Tier 1: Overview
General information about WeasyPrint, its capabilities, and system requirements. Start here if you're new to the library.

### Tier 2: API Reference
Detailed documentation of public APIs, classes, methods, and parameters. Use this section for integration and everyday development.

### Tier 3: CSS Support
Comprehensive coverage of supported CSS features, edge cases, and recommended usage patterns. This section helps you understand what's possible with WeasyPrint.

### Tier 4: Architecture and Internals
In-depth technical details about the internal structure, rendering pipeline, and component interactions. The architecture overview, PDF module, and CSS internals documents belong to this tier. This information is useful for contributors and those debugging complex issues.

### Tier 5: Failure Diagnostics
Detailed troubleshooting information, common failure modes, and recovery strategies. Reference this section when encountering problems.

## Documentation Structure

This documentation is available in two formats:

1. **JSON Files** (`/documentation/*.json`): Structured, machine-readable documentation that serves as the source of truth. These files can be programmatically accessed and processed.

2. **Markdown Files** (`/documentation/md/*.md`): Human-readable documentation generated from the JSON files. These files are optimized for reading and reference.

Additionally, the `/documentation/enhancements/` directory contains proposals for future improvements to WeasyPrint, with both JSON (machine-readable) and Markdown (human-readable) versions.

For more information about the documentation structure and how to use it effectively, see the [Documentation Guide](08_documentation_guide.md).

## Quick Links

- [GitHub Repository](https://github.com/Kozea/WeasyPrint)
- [Official Documentation](https://doc.courtbouillon.org/weasyprint)
- [Website](https://weasyprint.org)

## About This Documentation

This documentation was generated from structured JSON data by the Documentation Agent, analyzing the WeasyPrint codebase version 65.0.

- **Generation Date:** 2025-04-12
- **License:** BSD
- **Maintainer:** CourtBouillon (https://www.courtbouillon.org/)