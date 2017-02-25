---
layout: page
title: WeasyPrint 0.36
---

WeasyPrint 0.34, 0.35 and 0.36 have been released.

New features:

* [#407](https://github.com/Kozea/WeasyPrint/pull/407):
  Handle ::first-letter.
* [#423](https://github.com/Kozea/WeasyPrint/pull/423):
  Warn user about broken cairo versions.

Bug fixes:

* [#411](https://github.com/Kozea/WeasyPrint/pull/411):
  Typos fixed in command-line help.
* [#410](https://github.com/Kozea/WeasyPrint/pull/410):
  Fix AssertionError in split_text_box.
* [#398](https://github.com/Kozea/WeasyPrint/issues/398):
  Honor the presentational_hints option for PDFs.
* [#399](https://github.com/Kozea/WeasyPrint/pull/399):
  Avoid CairoSVG-2.0.0rc* on Python 2.
* [#396](https://github.com/Kozea/WeasyPrint/issues/396):
  Correctly close files open by mkstemp.
* [#403](https://github.com/Kozea/WeasyPrint/issues/403):
  Cast the number of columns into int.
* Fix multi-page multi-columns and add related tests.
