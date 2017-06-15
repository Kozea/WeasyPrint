---
layout: page
title: WeasyPrint 0.37
---

WeasyPrint 0.37 has been released.

WeasyPrint now depends on tinycss2 instead of tinycss.

New features:

* [437](https://github.com/Kozea/WeasyPrint/issues/437):
  Support local links in generated PDFs.

Bug fixes:

* [412](https://github.com/Kozea/WeasyPrint/issues/412):
  Use a NullHandler log handler when WeasyPrint is used as a library.
* [417](https://github.com/Kozea/WeasyPrint/issues/417),
  [472](https://github.com/Kozea/WeasyPrint/issues/472):
  Don't crash on some line breaks.
* [327](https://github.com/Kozea/WeasyPrint/issues/327):
  Don't crash with replaced elements with height set in percentages.
* [467](https://github.com/Kozea/WeasyPrint/issues/467):
  Remove incorrect line breaks.
* [446](https://github.com/Kozea/WeasyPrint/pull/446):
  Let the logging module do the string interpolation.
