---
layout: page
title: WeasyPrint 0.42
---

WeasyPrint 0.42 has been released.

WeasyPrint is not tested with (end-of-life) Python 3.3 anymore.

**This release is probably the last version of the 0.x series.**

Next version may include big changes:

- end of Python 2.7 support,
- initial support of bidirectional text,
- initial support of flexbox,
- improvements for speed and memory usage.

New features:

* [#532](https://github.com/Kozea/WeasyPrint/issues/532):
  Support relative file URIs when using CLI.

Bug fixes:

* [#553](https://github.com/Kozea/WeasyPrint/issues/553):
  Fix slow performance for pre-formatted boxes with a lot of children.
* [#409](https://github.com/Kozea/WeasyPrint/issues/409):
  Don't crash when rendering some tables.
* [#39](https://github.com/Kozea/WeasyPrint/issues/39):
  Fix rendering of floats in inlines.
* [#301](https://github.com/Kozea/WeasyPrint/issues/301):
  Split lines carefully.
* [#530](https://github.com/Kozea/WeasyPrint/issues/530):
  Fix root when frozen with Pyinstaller.
* [#534](https://github.com/Kozea/WeasyPrint/issues/534):
  Handle SVGs containing images embedded as data URIs.
* [#360](https://github.com/Kozea/WeasyPrint/issues/360):
  Fix border-radius rendering problem with some PDF readers.
* [#525](https://github.com/Kozea/WeasyPrint/issues/525):
  Fix pipenv support.
* [#227](https://github.com/Kozea/WeasyPrint/issues/227):
  Smartly handle replaced boxes with percentage width in auto-width parents.
* [#520](https://github.com/Kozea/WeasyPrint/issues/520):
  Don't ignore CSS `@page` rules that are imported by an `@import` rule.
