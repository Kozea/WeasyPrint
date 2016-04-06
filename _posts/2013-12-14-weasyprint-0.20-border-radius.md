---
layout: page
title: "WeasyPrint 0.20: Border radius"
---

WeasyPrint 0.20 has been released with new features and bug fixes.

* Add support for `border-radius`.
* Feature [#77](https://github.com/Kozea/WeasyPrint/issues/77>): Add PDF
  metadata from HTML.
* Feature [#12](https://github.com/Kozea/WeasyPrint/pull/12): Use html5lib.
* Tables: handle percentages for column groups, columns and cells, and values
  for row height.
* Bug fixes:
  * Fix [#84](https://github.com/Kozea/WeasyPrint/pull/84): don't crash when
    stylesheets are not available.
  * Fix [#101](https://github.com/Kozea/WeasyPrint/issues/101): use page ids
    instead of page numbers in PDF bookmarks.
  * Use `logger.warning` instead of deprecated `logger.warn`.
  * Add `font-stretch` in the `font` shorthand.
