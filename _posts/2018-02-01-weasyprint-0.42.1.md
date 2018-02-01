---
layout: page
title: WeasyPrint 0.42.1
---

WeasyPrint 0.42.1 has been released.

Versions 0.42.x will only get simple bug fixes backported from the master
branch. New features, opitimizations and complex bug fixes will only be added
to the 43+ versions that don't support Python 2 anymore.

Do not rely on future versions, development on the 0.x branch may be stopped at
any moment.

Bug fixes:

* [#566](https://github.com/Kozea/WeasyPrint/issues/566):
  Don't crash when using @font-config.
* [#567](https://github.com/Kozea/WeasyPrint/issues/567):
  Fix text-indent with text-align: justify.
* [#465](https://github.com/Kozea/WeasyPrint/issues/465):
  Fix string(*, start).
* [#562](https://github.com/Kozea/WeasyPrint/issues/562):
  Handle named pages with pseudo-class.
* [#507](https://github.com/Kozea/WeasyPrint/issues/507):
  Fix running headers.
* [#557](https://github.com/Kozea/WeasyPrint/issues/557):
  Avoid infinite loops in inline_line_width.
* [#555](https://github.com/Kozea/WeasyPrint/issues/555):
  Fix margins, borders and padding in column layouts.
