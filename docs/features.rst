Features
========

This page is for WeasyPrint |version|. See :doc:`changelog </changelog>`
for older versions.


URLs
----

WeasyPrint can read normal files, HTTP, FTP and `data URIs`_. It will follow
HTTP redirects but more advanced features like cookies and authentication
are currently not supported, although a custom :ref:`url fetcher
<url-fetchers>` can help.

.. _data URIs: http://en.wikipedia.org/wiki/Data_URI_scheme


HTML
----

Many HTML elements are implemented in CSS through the HTML5
`User-Agent stylesheet
<https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css>`_.

Some elements need special treatment:

* The ``<base>`` element, if present, determines the base for relative URLs.
* CSS stylesheets can be embedded in ``<style>`` elements or linked by
  ``<link rel=stylesheet>`` elements.
* ``<img>``, ``<embed>`` or ``<object>`` elements accept images either
  in raster formats supported by GdkPixbuf_ (including PNG, JPEG, GIF, ...)
  or in SVG with CairoSVG_. SVG images are not rasterized but rendered
  as vectors in the PDF output.

HTML `presentational hints`_ (like the ``width`` attribute on an ``img``
element) are **not** supported. Use CSS in the ``style`` attribute instead.

.. _CairoSVG: http://cairosvg.org/
.. _GdkPixbuf: https://live.gnome.org/GdkPixbuf
.. _presentational hints: http://www.w3.org/TR/html5/rendering.html#presentational-hints


PDF
---

In addition to text, raster and vector graphics, WeasyPrint’s PDF files
can contain hyperlinks, bookmarks and attachments.

Hyperlinks will be clickable in PDF viewers that support them. They can
be either internal, to another part of the same document (eg.
``<a href="#pdf">``) or external, to an URL. External links are resolved
to absolute URLs: ``<a href="/news/">`` on the WeasyPrint website would always
point to http://weasyprint.org/news/ in PDF files.

PDF bookmarks are also called outlines and are generally shown in a
sidebar. Clicking on an entry scrolls the matching part of the document
into view. By default all ``<h1>`` to ``<h6>`` titles generate bookmarks,
but this can be controlled with CSS (see :ref:`bookmarks`.)

Attachments are related files, embedded in the PDF itself. They can be
specified through ``<link rel=attachment>`` elements to add resources globally
or through regular links with ``<a rel=attachment>`` to attach a resource that
can be saved by clicking on said link. The ``title`` attribute can be used as
description of the attachment.


Fonts
-----

Although the CSS3 ``@font-face`` is not supported yet, WeasyPrint can use
any font that Pango can find installed on the system. If you can use a font
in a GTK+ application, just use it’s name in ``font-family``.
Copying a file into the ``~/.fonts`` directory is generally enough to install
a new font, depending on the OS.

Fonts are automatically embedded in PDF files.


CSS
---

CSS 2.1
~~~~~~~

The `CSS 2.1`_ features listed here are **not** supported:

* The `::first-line`_ and `::first-letter`_ pseudo-elements.
* On tables: `empty-cells`_ and `visibility: collapse`_.
* Minimum and maximum width_ and height_ on table-related boxes and
  page-margin boxes.
* Conforming `font matching algorithm`_. Currently ``font-family``
  is passed as-is to Pango.
* Right-to-left or `bi-directional text`_.
* `System colors`_ and `system fonts`_. The former are deprecated in CSS 3.

.. _CSS 2.1: http://www.w3.org/TR/CSS21/
.. _::first-line: http://www.w3.org/TR/CSS21/selector.html#first-line-pseudo
.. _::first-letter: http://www.w3.org/TR/CSS21/selector.html#first-letter
.. _empty-cells: http://www.w3.org/TR/CSS21/tables.html#empty-cells
.. _visibility\: collapse: http://www.w3.org/TR/CSS21/tables.html#dynamic-effects
.. _width: http://www.w3.org/TR/CSS21/visudet.html#min-max-widths
.. _height: http://www.w3.org/TR/CSS21/visudet.html#min-max-heights
.. _font matching algorithm: http://www.w3.org/TR/CSS21/fonts.html#algorithm
.. _Bi-directional text: http://www.w3.org/TR/CSS21/visuren.html#direction
.. _System colors: http://www.w3.org/TR/CSS21/ui.html#system-colors
.. _system fonts: http://www.w3.org/TR/CSS21/fonts.html#propdef-font

To the best of our knowledge, everything else that applies to the
print media **is** supported. Please report a bug if you find this list
incomplete.


CSS Selectors
~~~~~~~~~~~~~

With the exceptions noted here, all `Level 3 selectors`_ are supported.

PDF is generally not interactive. The ``:hover``, ``:active``, ``:focus``,
``:target`` and ``:visited`` pseudo-classes are accepted as valid but
never match anything.

Due to a limitation in cssselect_, ``*:first-of-type``, ``*:last-of-type``,
``*:nth-of-type``, ``*:nth-last-of-type`` and ``*:only-of-type`` are
not supported. They work when you specify an element type but parse
as invalid with ``*``.

.. _Level 3 selectors: http://www.w3.org/TR/css3-selectors/
.. _cssselect: http://packages.python.org/cssselect/


.. _hyphenation:

CSS Text: hyphenation
~~~~~~~~~~~~~~~~~~~~~


The experimental_ ``-weasy-hyphens`` property controls hyphenation
as described in `CSS 3 Text`_.
To get automatic hyphenation, you to set it to ``auto``
*and* have the ``lang`` HTML attribute set to one of the languages
`supported by Pyphen
<https://github.com/Kozea/Pyphen/tree/master/dictionaries>`_.

.. _CSS 3 Text: http://www.w3.org/TR/css3-text/#hyphens

.. code-block:: html

    <!doctype html>
    <html lang=en>
    <style>
      html { -weasy-hyphens: auto }
    </style>
    …

Automatic hyphenation can be disabled again with the ``manual`` value:

.. code-block:: css

    html { -weasy-hyphens: auto }
    a[href]::after { content: ' [' attr(href) ']'; -weasy-hyphens: manual }


.. _bookmarks:

CSS GCPM: bookmarks
~~~~~~~~~~~~~~~~~~~

PDF bookmarks are controlled as described in `CSS Generated Content for
Paged Media`_. This module is experimental_: the properties need to be
prefixed: use ``-weasy-bookmark-level`` and ``-weasy-bookmark-level``.

.. _CSS Generated Content for Paged Media: https://dvcs.w3.org/hg/csswg/raw-file/f7490857b4eb/css-gcpm/Overview.html#bookmarks
.. _experimental: http://www.w3.org/TR/css-2010/#experimental

For example, if you have only one top-level ``<h1>`` and do not wish to
include it in the bookmarks, add this in your stylesheet:

.. code-block:: css

    h1 { -weasy-bookmark-level: none }


Other CSS modules
~~~~~~~~~~~~~~~~~

The following features are supported:

* `CSS Colors Level 3`_ (except the deprecated System Colors)
* `CSS Paged Media`_ (except named pages)
* `CSS Transforms`_ (2D only)
* The background part of `CSS Backgrounds and Borders Level 3`_,
  including multiple background layers per element/box.
* ``linear-gradient()`` and ``radial-gradient()`` (as background images),
  from `CSS Images Level 3`_.
* The ``image-resolution`` property from `CSS Images Level 3`_.
  The ``snap`` and ``from-image`` values are not supported yet,
  so the property only takes a single ``<resolution>`` value.
* The ``box-sizing`` property from `CSS Basic User Interface`_:

.. _CSS Colors Level 3: http://www.w3.org/TR/css3-color/
.. _CSS Paged Media: http://dev.w3.org/csswg/css3-page/
.. _CSS Transforms: http://dev.w3.org/csswg/css3-transforms/
.. _CSS Backgrounds and Borders Level 3: http://www.w3.org/TR/css3-background/
.. _CSS Images Level 3: http://www.w3.org/TR/css3-images/
.. _CSS Basic User Interface: http://www.w3.org/TR/css3-ui/#box-sizing
