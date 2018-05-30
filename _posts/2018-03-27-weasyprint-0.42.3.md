---
layout: page
title: WeasyPrint 0.42.3
---

WeasyPrint 0.42.3 has been released.

Versions 0.42.x will only get simple bug fixes backported from the master
branch. New features, optimizations and complex bug fixes will only be added
to the 43+ versions that don't support Python 2 anymore.

Do not rely on future versions, development on the 0.x branch may be stopped at
any moment.

Bug fixes:

* [#583](https://github.com/Kozea/WeasyPrint/issues/583>):
  Fix floating-point number error to fix floating box layout
* [#586](https://github.com/Kozea/WeasyPrint/issues/586>):
  Don't optimize resume_at when splitting lines with trailing spaces
* [#582](https://github.com/Kozea/WeasyPrint/issues/582>):
  Fix table layout with no overflow
* [#580](https://github.com/Kozea/WeasyPrint/issues/580>):
  Fix inline box breaking function
* [#576](https://github.com/Kozea/WeasyPrint/issues/576>):
  Split replaced_min_content_width and replaced_max_content_width
* [#574](https://github.com/Kozea/WeasyPrint/issues/574>):
  Respect text direction and don't translate rtl columns twice
* [#569](https://github.com/Kozea/WeasyPrint/issues/569>):
  Get only first line's width of inline children to get linebox width
