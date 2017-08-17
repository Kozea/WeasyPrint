---
layout: page
title: WeasyPrint 0.40
---

WeasyPrint 0.40 has been released.

WeasyPrint now depends on cssselect2 instead of cssselect and lxml.

New features:

* [#57](https://github.com/Kozea/WeasyPrint/issues/57):
  Named pages.
* Unprefix properties, see
  [#498](https://github.com/Kozea/WeasyPrint/issues/498).
* Add a "verbose" option logging the document generation steps.

Bug fixes:

* [#483](https://github.com/Kozea/WeasyPrint/issues/483):
  Fix slow performance with long pre-formatted texts.
* [#70](https://github.com/Kozea/WeasyPrint/issues/70):
  Improve speed and memory usage for long documents.
* [#487](https://github.com/Kozea/WeasyPrint/issues/487):
  Don't crash on local() fonts with a space and no quotes.
