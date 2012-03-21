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

* `CSS 3 Colors`_
* `CSS 3 Selectors`_ except ``:lang``, ``:first-line`` and
  ``:first-letter``
* Experimental: `CSS 2D Transforms`_
* From `CSS 3 Backgrounds and Borders`_: ``background-clip``,
  ``background-origin`` and ``background-size``.
* Experimental: margin boxes, page counter and the ``size`` property
  from `CSS 3 Paged Media`_
* `box-sizing`_ from CSS3 Basic User Interface
* All of CSS 2.1 except:

  * Floats_
  * Absolute_, fixed_ and relative_ positioning and z-index_
  * `Inline blocks`_
  * `Automatic table layout`_, table `border collapsing`_ and the
    `empty-cells`_ property.
  * Minimum and maximum width_ and height_
  * `Vertical align`_ ``top`` and ``bottom`` (they are interpreted as
    ``text-top`` and ``text-bottom``, respectively)
  * Avoiding `page breaks`_ before or after an element
    (avoiding **inside** is supported)
  * Conforming `font matching algorithm`_. Currently ``font-family``
    is directly passed to Pango.
  * `Bi-directional text`_. (May happen to kind of work in uninterrupted text
    thanks to Pango)

.. _CairoSVG: http://cairosvg.org/
.. _ImageMagick: http://www.imagemagick.org/script/formats.php
.. _presentational hints: http://www.w3.org/TR/html5/rendering.html#presentational-hints
.. _CSS 3 Colors: http://www.w3.org/TR/css3-color/
.. _CSS 3 Selectors: http://www.w3.org/TR/css3-selectors/
.. _CSS 3 Backgrounds and Borders: http://www.w3.org/TR/css3-background/
.. _box-sizing: http://www.w3.org/TR/css3-ui/#box-sizing
.. _Floats: http://www.w3.org/TR/CSS21/visuren.html#floats
.. _Absolute: http://www.w3.org/TR/CSS21/visuren.html#absolute-positioning
.. _fixed: http://www.w3.org/TR/CSS21/visuren.html#fixed-positioning
.. _z-index: http://www.w3.org/TR/CSS21/visuren.html#layers
.. _relative: http://www.w3.org/TR/CSS21/visuren.html#relative-positioning
.. _Automatic table layout: http://www.w3.org/TR/CSS21/tables.html#auto-table-layout
.. _Inline blocks: http://www.w3.org/TR/CSS21/visuren.html#value-def-inline-block
.. _border collapsing: http://www.w3.org/TR/CSS21/tables.html#collapsing-borders
.. _empty-cells: http://www.w3.org/TR/CSS21/tables.html#empty-cells
.. _width: http://www.w3.org/TR/CSS21/visudet.html#min-max-widths
.. _height: http://www.w3.org/TR/CSS21/visudet.html#min-max-heights
.. _Vertical align: http://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align
.. _page breaks: http://www.w3.org/TR/CSS21/page.html#page-breaks
.. _font matching algorithm: http://www.w3.org/TR/CSS21/fonts.html#algorithm
.. _Bi-directional text: http://www.w3.org/TR/CSS21/visuren.html#direction


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
