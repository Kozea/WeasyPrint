Documentation
=============

* `Installing </install/>`_
* `Using </using/>`_
* `Hacking </hacking/>`_
* **Features**

Features
~~~~~~~~

(For older versions, see the changelog_.)

.. _changelog: https://github.com/Kozea/WeasyPrint/blob/master/CHANGES

WeasyPrint 0.10 supports:

* HTML documents with:

  * Linked and embedded CSS stylesheets
  * Images in ``<img>``, ``<embed>`` or ``<object>`` elements:

    - Raster images formats supported by ImageMagick_ (includes
      PNG, JPEG, GIF, ...)
    - SVG images with CairoSVG_

  * Hyperlinks, either internal (with the target in the same document:
    ``<a href="#foo">``) or external. The links are clickable in PDF viewers
    that support them.
  * **Not** supported: HTML `presentational hints`_ (like the ``width``
    attribute on an ``img`` element). Use CSS in the ``style``
    attribute instead.

* Most of `CSS 2.1`_ (see below__)
* Most `CSS 3 Selectors`_ (see below__)
* `CSS 3 Colors`_
* Bookmarks from `CSS Generated Content for Paged Media`_
* Experimental: `CSS 2D Transforms`_
* From `CSS 3 Backgrounds and Borders`_: ``background-clip``,
  ``background-origin`` and ``background-size``.
* Experimental: margin boxes, page counter and the ``size`` property
  from `CSS 3 Paged Media`_
* `box-sizing`_ from CSS3 Basic User Interface

.. _PDF bookmarks: #pdf-bookmarks
__ #missing-css-2-1-features
__ #missing-css-3-selectors

.. _CairoSVG: http://cairosvg.org/
.. _ImageMagick: http://www.imagemagick.org/script/formats.php
.. _presentational hints: http://www.w3.org/TR/html5/rendering.html#presentational-hints
.. _CSS 2.1: http://www.w3.org/TR/CSS21/
.. _CSS 3 Colors: http://www.w3.org/TR/css3-color/
.. _CSS 3 Selectors: http://www.w3.org/TR/css3-selectors/
.. _CSS 3 Backgrounds and Borders: http://www.w3.org/TR/css3-background/
.. _box-sizing: http://www.w3.org/TR/css3-ui/#box-sizing

Experimental features
~~~~~~~~~~~~~~~~~~~~~

These features are only described in *Working Draft* specification.
As they are `at risk of changing`_, you need to use th ``-weasy-`` prefix
to use them.

WeasyPrint tries to follow specification changes. Be aware of this if you
use any experimental feature!

* The ``size`` property from `CSS 3 Paged Media`_ to set the page size.
  Use ``-weasy-size``.

* `CSS 2D Transforms`_: use ``-weasy-transform`` and
  ``-weasy-transform-origin``.

* Bookmarks from `CSS Generated Content for Paged Media`_: use
  ``-weasy-bookmark-level`` and ``-weasy-bookmark-level``.

.. _at risk of changing: http://www.w3.org/TR/css-2010/#experimental
.. _CSS 3 Paged Media: http://www.w3.org/TR/css3-page/
.. _CSS 2D Transforms: http://www.w3.org/TR/css3-2d-transforms/
.. _CSS Generated Content for Paged Media: http://dev.w3.org/csswg/css3-gcpm/#bookmarks


Missing CSS 3 selectors
~~~~~~~~~~~~~~~~~~~~~~~

Selectors in WeasyPrint are based on cssselect_ and share its limitations.
Namely:

* ``*:first-of-type``, ``*:last-of-type``, ``*:nth-of-type``,
  ``*:nth-last-of-type`` and ``*:only-of-type`` are not supported.
  They work when you specify an element type but parse as invalid with ``*``.
* ``:hover``, ``:active``, ``:focus``, ``:target`` and ``:visited``
  are accepted but never match anything.

.. _cssselect: http://packages.python.org/cssselect/


Missing CSS 2.1 features
~~~~~~~~~~~~~~~~~~~~~~~~

To the best of our knowledge, everything in CSS 2.1 that applies to the
“print” media but is not listed in this section is supported by WeasyPrint.
Please `report a bug`_ if you find this list incomplete.

.. _report a bug: /community/#issue-bug-tracker

Some CSS 2.1 features are not supported yet but are on the *to do* list:

* Floats_
* Table `border collapsing`_ and the `empty-cells`_ property.
* Minimum and maximum width_ and height_ on table-related and page-related
  boxes
* Outlines_

We have few or no use cases for others, but feel free to ask about them:

* Conforming `font matching algorithm`_. Currently ``font-family``
  is directly passed to Pango.
* Right-to-left or `bi-directional text`_.
  (May happen to kind of work in uninterrupted text thanks to Pango)
* `System colors`_. They are deprecated in CSS 3

.. _Floats: http://www.w3.org/TR/CSS21/visuren.html#floats
.. _border collapsing: http://www.w3.org/TR/CSS21/tables.html#collapsing-borders
.. _empty-cells: http://www.w3.org/TR/CSS21/tables.html#empty-cells
.. _width: http://www.w3.org/TR/CSS21/visudet.html#min-max-widths
.. _height: http://www.w3.org/TR/CSS21/visudet.html#min-max-heights
.. _font matching algorithm: http://www.w3.org/TR/CSS21/fonts.html#algorithm
.. _Bi-directional text: http://www.w3.org/TR/CSS21/visuren.html#direction
.. _System colors: http://www.w3.org/TR/CSS21/ui.html#system-colors
.. _Outlines: http://www.w3.org/TR/CSS21/ui.html#dynamic-outlines
