---
layout: page
title: WeasyPrint 43rc1
---

WeasyPrint 43rc1 has been released.

**This version is experimental, don't use it in production. If you find bugs,
please report them!**

You can read the [list of open tickets that will be closed before version
43](https://github.com/Kozea/WeasyPrint/milestone/10) and tell us if you need
another issue to be added into this list.

## Dependencies

* Python 3.4+ is now needed, Python 2.x is not supported anymore
* Cairo 1.15.4+ is now needed, but 1.10+ should work with missing features
  (such as links, outlines and metadata)
* Pdfrw is not needed anymore

## New features

* `Beautiful website <https://weasyprint.org>`_
* `#579 <https://github.com/Kozea/WeasyPrint/issues/579>`_:
  Initial support of flexbox
* `#592 <https://github.com/Kozea/WeasyPrint/pull/592>`_:
  Support @font-face on Windows
* `#306 <https://github.com/Kozea/WeasyPrint/issue/306>`_:
  Add a timeout parameter to the URL fetcher functions
* `#594 <https://github.com/Kozea/WeasyPrint/pull/594>`_:
  Split tests using modern pytest features
* `#599 <https://github.com/Kozea/WeasyPrint/pull/599>`_:
  Make tests pass on Windows
* `#604 <https://github.com/Kozea/WeasyPrint/pull/604>`_:
  Handle target counters and target texts
* `#631 <https://github.com/Kozea/WeasyPrint/pull/631>`_:
  Enable counter-increment and counter-reset in page context
* `#622 <https://github.com/Kozea/WeasyPrint/issue/622>`_:
  Allow pathlib.Path objects for HTML, CSS and Attachment classes
* `#674 <https://github.com/Kozea/WeasyPrint/issue/674>`_:
  Add extensive installation instructions for Windows

## Bug fixes

* `#558 <https://github.com/Kozea/WeasyPrint/issues/558>`_:
  Fix attachments
* `#565 <https://github.com/Kozea/WeasyPrint/issues/565>`_,
  `#596 <https://github.com/Kozea/WeasyPrint/issues/596>`_,
  `#539 <https://github.com/Kozea/WeasyPrint/issues/539>`_:
  Fix many PDF rendering, printing and compatibility problems
* `#614 <https://github.com/Kozea/WeasyPrint/issues/614>`_:
  Avoid crashes and endless loops caused by a Pango bug
* `#662 <https://github.com/Kozea/WeasyPrint/pull/662>`_:
  Fix warnings and errors when generating documentation
* `#666 <https://github.com/Kozea/WeasyPrint/issues/666>`_,
  `#685 <https://github.com/Kozea/WeasyPrint/issues/685>`_:
  Fix many table layout rendering problems
* `#680 <https://github.com/Kozea/WeasyPrint/pull/680>`_:
  Don't crash when there's no font available
* `#662 <https://github.com/Kozea/WeasyPrint/pull/662>`_:
  Fix support of some align values in tables
