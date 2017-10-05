---
layout: page
title: WeasyPrint 0.41
---

WeasyPrint 0.41 has been released.

WeasyPrint now depends on pdfrw >= 0.4.

New features:

* [#471](https://github.com/Kozea/WeasyPrint/issues/471):
  Support page marks and bleed.

Bug fixes:

* [#513](https://github.com/Kozea/WeasyPrint/issues/513):
  Don't crash on unsupported image-resolution values.
* [#506](https://github.com/Kozea/WeasyPrint/issues/506):
  Fix @font-face use with write_* methods.
* [#500](https://github.com/Kozea/WeasyPrint/pull/500):
  Improve readability of _select_source function.
* [#498](https://github.com/Kozea/WeasyPrint/issues/498):
  Use CSS prefixes as recommanded by the CSSWG.
* [#441](https://github.com/Kozea/WeasyPrint/issues/441):
  Fix rendering problems and crashes when using @font-face.
* [bb3a4db](https://github.com/Kozea/WeasyPrint/commit/bb3a4db):
  Try to break pages after a block before trying to break inside it.
* [1d1654c](https://github.com/Kozea/WeasyPrint/commit/1d1654c):
  Fix and test corner cases about named pages.

Documentation:

* [#508](https://github.com/Kozea/WeasyPrint/pull/508):
  Add missing libpangocairo dependency for Debian and Ubuntu.
* [a7b17fb](https://github.com/Kozea/WeasyPrint/commit/a7b17fb):
  Add documentation on logged rendering steps.
