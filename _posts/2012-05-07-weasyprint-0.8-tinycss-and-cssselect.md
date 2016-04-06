---
layout: page
title: WeasyPrint 0.8, tinycss and cssselect
---

Some [new features](https://github.com/Kozea/WeasyPrint/blob/master/CHANGES) as
usual. The big one is *automatic layout* for tables. Roughly, columns will get
their width determined by the amount of content.

Other important but more underlying changes are
[tinycss](http://packages.python.org/tinycss/) and
[cssselect](http://packages.python.org/cssselect/). tinycss is a new CSS parser
I wrote from scratch as a smaller and faster alternative to
[cssutils](http://packages.python.org/cssutils/). You can
[read more about it](http://exyr.org/2012/tinycss-css-parser/) on my blog. As
to cssselect, I took over its maintenance after extracting it from
[lxml](http://lxml.de/). It now supports most Level 3 selectors and can be
extended more easily.
