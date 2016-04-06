---
layout: page
title: "WeasyPrint 0.12: border-collapse and Flask-WeasyPrint"
---

WeasyPrint 0.12 is out.

This release adds support for the collapsing border model of tables, through
the `border-collapse` property. Previously, table borders were always
separated. This new model is incompatible with table headers and footers:
with `border-collapse: collapse`, `<thead>` and `<tfoot>` elements
are treated like normal `<tbody>` groups and are not repeated on each page.

On an unrelated note, 0.12 also adds the [URL fetcher](/using/#url-fetchers)
hook to the public API. It allows to control or override how WeasyPrint
accesses HTTP or other URLs for HTML documents, CSS stylesheets, and images.

[Flask-WeasyPrint](http://packages.python.org/Flask-WeasyPrint/) is
a new extension that makes use of an URL fetcher to integrate WeasyPrint
in a Flask application.
