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
in a GTK+ application, just use its name in ``font-family``.

Fonts are automatically embedded in PDF files.

On Windows and MacOS X, Pango uses the native font-managing libraries. You can
use the tools provided by your OS to know which fonts are available.

On Linux, Pango uses fontconfig to access fonts. You can list the available
fonts thanks to the ``fc-list`` command, and know which font is matched by a
given pattern thanks to ``fc-match``. Copying a font file into the
``~/.local/share/fonts`` or ``~/.fonts`` directory is generally enough to
install a new font.


CSS
---

WeasyPrint supports many of the `CSS specifications`_ written by the W3C. You
will find in this chapter a comprehensive list of the specifications or drafts
with at least one feature implemented in WeasyPrint.

The results of some of the test suites provided by the W3C are also available
at `test.weasyprint.org`_. This website uses a tool called `WeasySuite`_ that
can be useful if you want to implement new features in WeasyPrint.

.. _CSS specifications: https://www.w3.org/Style/CSS/current-work
.. _test.weasyprint.org: http://test.weasyprint.org/
.. _WeasySuite: https://github.com/Kozea/WeasySuite


CSS Level 2 Revision 1
~~~~~~~~~~~~~~~~~~~~~~

The `CSS Level 2 Revision 1`_ specification, best known as CSS 2.1, is pretty
well supported by WeasyPrint. Since version 0.11, it passes the famous `Acid2
Test`_.

The CSS 2.1 features listed here are **not** supported:

* The `::first-line`_ and `::first-letter`_ pseudo-elements.
* On tables: `visibility: collapse`_.
* Minimum and maximum height_ on table-related boxes.
* Minimum and maximum width_ and height_ on page-margin boxes.
* Conforming `font matching algorithm`_. Currently ``font-family``
  is passed as-is to Pango.
* Right-to-left or `bi-directional text`_.
* `System colors`_ and `system fonts`_. The former are deprecated in `CSS Color
  Module Level 3`_.

.. _CSS Level 2 Revision 1: http://www.w3.org/TR/CSS21/
.. _Acid2 Test: http://www.webstandards.org/files/acid2/test.html
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


Selectors Level 3
~~~~~~~~~~~~~~~~~

With the exceptions noted here, all `Selectors Level 3`_ are supported.

PDF is generally not interactive. The ``:hover``, ``:active``, ``:focus``,
``:target`` and ``:visited`` pseudo-classes are accepted as valid but
never match anything.

Due to a limitation in cssselect_, ``*:first-of-type``, ``*:last-of-type``,
``*:nth-of-type``, ``*:nth-last-of-type`` and ``*:only-of-type`` are
not supported. They work when you specify an element type but parse
as invalid with ``*``.

.. _Selectors Level 3: http://www.w3.org/TR/css3-selectors/
.. _cssselect: http://packages.python.org/cssselect/


CSS Text Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Text Module Level 3`_ is a working draft defining "properties for text
manipulation" and covering "line breaking, justification and alignment, white
space handling, and text transformation".

Among its features, some are already included in CSS 2.1 (``line-break``,
``word-break``).

One new property is supported by WeasyPrint: the experimental_
``-weasy-hyphens`` property controling hyphenation_.

To get automatic hyphenation, you to set it to ``auto``
*and* have the ``lang`` HTML attribute set to one of the languages
`supported by Pyphen
<https://github.com/Kozea/Pyphen/tree/master/pyphen/dictionaries>`_.

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

The other features provided by `CSS Text Module Level 3`_ are **not**
supported:

- the ``full-width`` value of the ``text-transform`` property;
- the ``tab-size`` property;
- the ``line-break`` and ``word-break`` properties;
- the ``overflow-wrap`` property replacing ``word-wrap``.
- the ``start``, ``end``, ``match-parent`` and ``start end`` values of the
  ``text-align`` property;
- the ``text-align-last`` and ``text-justify`` properties;
- the ``text-indent`` and ``hanging-punctuation`` properties.

.. _CSS Text Module Level 3: http://www.w3.org/TR/css3-text/
.. _hyphenation: http://www.w3.org/TR/css3-text/#hyphenation


CSS Paged Media Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Paged Media Module Level 3`_ is a working draft including features for
paged media "describing how:

- page breaks are created and avoided;
- the page properties such as size, orientation, margins, border, and padding
  are specified;
- headers and footers are established within the page margins;
- content such as page counters are placed in the headers and footers; and
- orphans and widows can be controlled."

One feature from this document is **not** implemented: `named pages`. All the
other features are available, including:

- the ``@page`` rule and the ``:left``, ``:right``, ``:first`` and ``:blank``
  selectors;
- the page margin boxes;
- the page-based counters (with known bugs `#91`_, `#93`_, `#289`_);
- the page ``size`` property.

.. _CSS Paged Media Module Level 3: http://dev.w3.org/csswg/css3-page/
.. _named pages: http://dev.w3.org/csswg/css3-page/#using-named-pages
.. _#91: https://github.com/Kozea/WeasyPrint/issues/91
.. _#93: https://github.com/Kozea/WeasyPrint/issues/93
.. _#289: https://github.com/Kozea/WeasyPrint/issues/289


.. _bookmarks:

CSS Generated Content for Paged Media Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Generated Content for Paged Media Module`_ (GCPM) is a working draft
defining "new properties and values, so that authors may bring new techniques
(running headers and footers, footnotes, leaders, bookmarks) to paged media".

Two features from this module have been implemented in WeasyPrint.

The first feature is `PDF bookmarks`_.  Using the experimental_
``-weasy-bookmark-level`` and ``-weasy-bookmark-level`` properties, you can add
bookmarks that will be available in your PDF reader.

Bookmarks have already been added in the WeasyPrint's `user agent stylesheet`_,
so your generated documents will automatically have bookmarks on headers (from
``<h1>`` to ``<h6>``). But for example, if you have only one top-level ``<h1>``
and do not wish to include it in the bookmarks, add this in your stylesheet:

.. code-block:: css

    h1 { -weasy-bookmark-level: none }

The second feature is `Named strings`_. You can define strings related to the
first or last element of a type present on a page, and display these strings in
page borders. This feature is really useful to add the title of the current
chapter at the top of the pages of a book for example.

The named strings can embed static strings, counters, tag contents and tag
attributes.

.. code-block:: css

    @top-center { content: string(chapter); }
    h2 { -weasy-string-set: chapter "Current chapter: " content() }

The other features of GCPM are **not** implemented:

- running elements (``running()`` and ``element()``);
- footnotes (``float: footnote``, ``footnote-display``, ``footnote`` counter,
  ``::footnote-call``, ``::footnote-marker``, ``@footnote`` rule,
  ``footnote-policy``);
- page selectors and page groups (``:nth()`` pseudo-class);
- leaders (``content: leader()``);
- cross-references (``target-counter()``, ``target-counters()`` and
  ``target-text()``);
- bookmark states (``bookmark-state``).

.. _CSS Generated Content for Paged Media Module: http://www.w3.org/TR/css-gcpm-3/
.. _PDF bookmarks: http://www.w3.org/TR/css-gcpm-3/#bookmarks
.. _Named strings: http://www.w3.org/TR/css-gcpm-3/#named-strings
.. _experimental: http://www.w3.org/TR/css-2010/#experimental
.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css


CSS Color Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Color Module Level 3`_ is a recommandation defining "CSS properties
which allow authors to specify the foreground color and opacity of an
element". Its main goal is to specify how colors are defined, including color
keywords and the ``#rgb``, ``#rrggbb``, ``rgb()``, ``rgba()``, ``hsl()``,
``hsla()`` syntaxes. Opacity and alpha compositing are also defined in this
document.

This recommandation is fully implemented in WeasyPrint, except the deprecated
System Colors.

.. _CSS Color Module Level 3: http://www.w3.org/TR/css3-color/


CSS Transforms Module Level 1
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Transforms Module Level 1`_ working draft "describes a coordinate
system within each element is positioned. This coordinate space can be modified
with the transform property. Using transform, elements can be translated,
rotated and scaled in two or three dimensional space."

WeasyPrint supports the ``transform`` and ``transform-origin`` properties, and
all the 2D transformations (``matrix``, ``rotate``, ``translate(X|Y)?``,
``scale(X|Y)?``, ``skew(X|Y)?``).

WeasyPrint does **not** support the ``transform-style``, ``perspective``,
``perspective-origin`` and ``backface-visibility`` properties, and all the 3D
transformations (``matrix3d``, ``rotate(3d|X|Y|Z)``, ``translate(3d|Z)``,
``scale(3d|Z)``).

.. _CSS Transforms Module Level 1: http://dev.w3.org/csswg/css3-transforms/


CSS Backgrounds and Borders Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Backgrounds and Borders Module Level 3`_ is a candidate recommandation
defining properties dealing "with the decoration of the border area and with
the background of the content, padding and border areas".

The `border part`_ of this module is supported, as it is already included in
the the CSS 2.1 specification.

WeasyPrint supports the `background part`_ of this module (allowing multiple
background layers per box), including the ``background``, ``background-color``,
``background-image``, ``background-repeat``, ``background-attachment``,
``background-position``, ``background-clip``, ``background-origin`` and
``background-size`` properties.

WeasyPrint also supports the `rounded corners part`_ of this module, including
the ``border-radius`` property.

WeasyPrint does **not** support the `border images part`_ of this module,
including the ``border-image``, ``border-image-source``,
``border-image-slice``, ``border-image-width``, ``border-image-outset`` and
``border-image-repeat`` properties.

WeasyPrint does **not** support the `box shadow part`_ of this module,
including the ``box-shadow`` property. This feature has been implemented in a
`git branch`_ that is not released, as it relies on raster implementation of
shadows.

.. _CSS Backgrounds and Borders Level 3: http://www.w3.org/TR/css3-background/
.. _border part: http://www.w3.org/TR/css3-background/#borders
.. _background part: http://www.w3.org/TR/css3-background/#backgrounds
.. _rounded corners part: http://www.w3.org/TR/css3-background/#corners
.. _border images part: http://www.w3.org/TR/css3-background/#border-images
.. _box shadow part: http://www.w3.org/TR/css3-background/#misc
.. _git branch: https://github.com/Kozea/WeasyPrint/pull/149


CSS Image Values and Replaced Content Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `Image Values and Replaced Content Module Level 3`_ is a candidate
recommandation introducing "additional ways of representing 2D images, for
example as a list of URIs denoting fallbacks, or as a gradient", defining
"several properties for manipulating raster images and for sizing or
positioning replaced elements" and "generic sizing algorithm for replaced
elements".

The ``linear-gradient()``, ``radial-gradient()`` and
``repeating-radial-gradient()`` properties are supported as background images.

The the ``url()`` notation is supported, but the ``image()`` notation is
**not** supported for background images.

The ``from-image`` and ``snap`` values of the ``image-resolution`` property are
**not** supported, but the ``resolution`` value is supported.

The ``image-orientation``, ``object-fit`` and ``object-position`` are **not**
supported.

.. _Image Values and Replaced Content Module Level 3: http://www.w3.org/TR/css3-images/


CSS Basic User Interface Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Basic User Interface Module Level 3`_ also known as CSS3 UI is a
candidate recommandation describing "CSS properties which enable authors to
style user interface related properties and values."

Only one new property defined in this document is implemented in WeasyPrint:
the ``box-sizing`` property.

Some of the properties do not apply for WeasyPrint: ``cursor``, ``resize``,
``caret-color``, ``nav-(up|right|down|left)``.

The other properties are **not** implemented: ``outline-offset`` and
``text-overflow``.

.. _CSS Basic User Interface Module Level 3: http://www.w3.org/TR/css-ui-3/


CSS Values and Units Module Level 3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `CSS Values and Units Module Level 3`_ defines various units and
keywords used in "value definition field of each CSS property".

The ``initial`` and ``inherit`` CSS-wide keywords are supported, but the
``unset`` keyword is **not** supported.

Quoted strings, URLs and numeric data types are supported.

Font-related lengths (``em``, ``ex``, ``ch``, ``rem``), absolute lengths
(``cm``, ``mm``, ``q``, ``in``, ``pt``, ``pc``, ``px``), angles (``rad``,
``grad``, ``turn``, ``deg``), resolutions (``dpi``, ``dpcm``, ``dppx``) are
supported.

The ``attr()`` functional notation is allowed in the ``content`` and
``string-set`` properties.

Viewport-percentage lengths (``vw``, ``vh``, ``vmin``, ``vmax``) are **not**
supported.

.. _CSS Values and Units Module Level 3: https://www.w3.org/TR/css3-values/
