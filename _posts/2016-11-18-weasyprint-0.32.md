---
layout: page
title: WeasyPrint 0.32
---

WeasyPrint 0.32 has been released.

New features:

* [#28](https://github.com/Kozea/WeasyPrint/issues/28):
  Support @font-face on Linux.
* Support CSS fonts level 3 almost entirely, including OpenType features.
* [#253](https://github.com/Kozea/WeasyPrint/issues/253):
  Support presentational hints (optional).
* Support break-after, break-before and break-inside for pages and columns.
* [#384](https://github.com/Kozea/WeasyPrint/issues/384):
  Major performance boost.

Bux fixes:

* [#368](https://github.com/Kozea/WeasyPrint/issues/368):
  Respect white-space for shrink-to-fit.
* [#382](https://github.com/Kozea/WeasyPrint/issues/382):
  Fix the preferred width for column groups.
* Handle relative boxes in column-layout boxes.

Documentation:

* Add more and more documentation about Windows installation.
* [#355](https://github.com/Kozea/WeasyPrint/issues/355):
  Add fonts requirements for tests.
