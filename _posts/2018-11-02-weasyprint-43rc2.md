---
layout: page
title: WeasyPrint 43rc2
---

WeasyPrint 43rc2 has been released.

**This version is experimental, don't use it in production. If you find bugs,
please report them!**

### Bug fixes

* [#706](https://github.com/Kozea/WeasyPrint/issues/706):
  Fix text-indent at the beginning of a page
* [#687](https://github.com/Kozea/WeasyPrint/issues/687):
  Allow query strings in file:// URIs
* [#720](https://github.com/Kozea/WeasyPrint/issues/720):
  Optimize minimum size calculation of long inline elements
* [#717](https://github.com/Kozea/WeasyPrint/issues/717):
  Display `<details>` tags as blocks
* [#691](https://github.com/Kozea/WeasyPrint/issues/691):
  Don't recalculate max content widths when distributing extra space for tables
* [#722](https://github.com/Kozea/WeasyPrint/issues/722):
  Fix bookmarks and strings set on images
* [#723](https://github.com/Kozea/WeasyPrint/issues/723):
  Warn users when string() is not used in page margin
