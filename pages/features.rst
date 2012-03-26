Documentation
=============

* `Installing </install/>`_
* `Using </using/>`_
* `Hacking </hacking/>`_
* **Features**

Features
~~~~~~~~

WeasyPrint 0.7 supports:

(For older versions, see the changelog_.)

.. _changelog: https://github.com/Kozea/WeasyPrint/blob/master/CHANGES

* HTML documents with:

  * Linked and embedded CSS stylesheets
  * Images in ``<img>``, ``<embed>`` or ``<object>`` elements:

    - Raster images formats supported by ImageMagick_ (includes
      PNG, JPEG, GIF, ...)
    - SVG images with CairoSVG_

  * **Not** supported: HTML `presentational hints`_ (like the ``width``
    attribute on an ``img`` element). Use CSS in the ``style``
    attribute instead.

* Most of `CSS 2.1`_ (see below__)
* Most `CSS 3 Selectors`_ (see below__)
* `CSS 3 Colors`_
* Experimental: `CSS 2D Transforms`_
* From `CSS 3 Backgrounds and Borders`_: ``background-clip``,
  ``background-origin`` and ``background-size``.
* Experimental: margin boxes, page counter and the ``size`` property
  from `CSS 3 Paged Media`_
* `box-sizing`_ from CSS3 Basic User Interface

__ #missing-css-2-1-features
__ #missing-css-3-selectors

.. _CairoSVG: http://cairosvg.org/
.. _ImageMagick: http://www.imagemagick.org/script/formats.php
.. _presentational hints: http://www.w3.org/TR/html5/rendering.html#presentational-hints
.. _CSS 2.1: http://www.w3.org/TR/CSS21/
.. _CSS 3 Colors: http://www.w3.org/TR/css3-color/
.. _CSS 3 Selectors: http://www.w3.org/TR/css3-selectors/
.. _should be: https://github.com/lxml/lxml/pull/22
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

.. _at risk of changing: http://www.w3.org/TR/css-2010/#experimental
.. _CSS 3 Paged Media: http://www.w3.org/TR/css3-page/
.. _CSS 2D Transforms: http://www.w3.org/TR/css3-2d-transforms/


Missing CSS 3 selectors
~~~~~~~~~~~~~~~~~~~~~~~

Selectors in WeasyPrint are based on lxml.cssselect_ and share some of its
limitations. (But not all: there is special support for pseudo-elements.
``:before`` and ``:after`` *are* supported.)

.. _lxml.cssselect: http://lxml.de/cssselect.html

Some pseudo-classes and pseudo-elements are not supported:

* ``:root`` `should be`_ in the next lxml release
* ``:first-line`` and ``:first-letter``
* ``:lang(language)``
* Link state: ``:link`` and ``:visited``
* Actions: ``:hover``, ``:active``, ``:focus`` and ``:target``
* UI state: ``:enabled`` and ``:disabled``
* ``*:first-of-type``, ``*:last-of-type``, ``*:nth-of-type``,
  ``*:nth-last-of-type``, ``*:only-of-type``.
  All of these work when you specify an element type, but not with ``*``


Missing CSS 2.1 features
~~~~~~~~~~~~~~~~~~~~~~~~

To the best of our knowledge, everything in CSS 2.1 (selectors aside, see
above) that applies to the “print” media but is not listed in this section
is supported by WeasyPrint. Please `report a bug`_ if you find this list
incomplete.

.. _report a bug: /community/#issue-bug-tracker

Some CSS 2.1 features are not supported yet but are on the *to do* list:

* Floats_
* Absolute_, fixed_ and relative_ positioning and z-index_
* `Inline blocks`_ and `inline tables`_
* `Automatic table layout`_, table `border collapsing`_ and the
  `empty-cells`_ property.
* Minimum and maximum width_ and height_
* Avoiding `page breaks`_ before or after an element
  (avoiding **inside** is supported)
* `Vertical align`_ ``top`` and ``bottom`` (they are interpreted as
  ``text-top`` and ``text-bottom``, respectively)
* Outlines_

Others are not planned for now:

* Conforming `font matching algorithm`_. Currently ``font-family``
  is directly passed to Pango.
* `Bi-directional text`_. (May happen to kind of work in uninterrupted text
  thanks to Pango)
* `System colors`_ are deprecated in CSS 3

.. _Floats: http://www.w3.org/TR/CSS21/visuren.html#floats
.. _Absolute: http://www.w3.org/TR/CSS21/visuren.html#absolute-positioning
.. _fixed: http://www.w3.org/TR/CSS21/visuren.html#fixed-positioning
.. _z-index: http://www.w3.org/TR/CSS21/visuren.html#layers
.. _relative: http://www.w3.org/TR/CSS21/visuren.html#relative-positioning
.. _Automatic table layout: http://www.w3.org/TR/CSS21/tables.html#auto-table-layout
.. _Inline blocks: http://www.w3.org/TR/CSS21/visuren.html#value-def-inline-block
.. _inline tables: http://www.w3.org/TR/CSS21/tables.html#value-def-inline-table
.. _border collapsing: http://www.w3.org/TR/CSS21/tables.html#collapsing-borders
.. _empty-cells: http://www.w3.org/TR/CSS21/tables.html#empty-cells
.. _width: http://www.w3.org/TR/CSS21/visudet.html#min-max-widths
.. _height: http://www.w3.org/TR/CSS21/visudet.html#min-max-heights
.. _Vertical align: http://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align
.. _page breaks: http://www.w3.org/TR/CSS21/page.html#page-breaks
.. _font matching algorithm: http://www.w3.org/TR/CSS21/fonts.html#algorithm
.. _Bi-directional text: http://www.w3.org/TR/CSS21/visuren.html#direction
.. _System colors: http://www.w3.org/TR/CSS21/ui.html#system-colors
.. _Outlines: http://www.w3.org/TR/CSS21/ui.html#dynamic-outlines
