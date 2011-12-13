Documentation
=============

* `Installing </install/>`_
* `Using </using/>`_
* `Hacking </hacking/>`_
* **Features**

Features
~~~~~~~~

WeasyPrint 0.3 supports:

(For older versions, see the changelog_.)

.. _changelog: https://github.com/Kozea/WeasyPrint/blob/master/CHANGES

* HTML documents with:

  * Linked and embedded CSS stylesheets
  * Raster and SVG images in ``<img>`` elements. (Support for raster file
    formats is that of the PIL_)

* `CSS 3 Colors`_ except the ``opacity`` property.
* `CSS 3 Selectors`_ except ``:lang``, ``:first-line`` and
  ``:first-letter``
* Part of `CSS 3 Paged Media`_: page size, borders, padding and margins
* `box-sizing`_ form CSS3 Basic User Interface
* All of CSS 2.1 except:

  * Floats_
  * Absolute_, fixed_ and relative_ positioning and z-index_
  * `Inline blocks`_
  * `Automatic table layout`_ and table `border collapsing`_
  * `Collapsing margins`_
  * Minimum and maximum width_ and height_
  * Overflow_ and clip
  * `Border styles`_ ``double``, ``groove``, ``ridge``, ``inset`` and ``outset``
  * `Vertical align`_ ``top`` and ``bottom`` (they are interpreted as
    ``text-top`` and ``text-bottom``, respectively)
  * `Letter and word spacing`_
  * `Justified text`_
  * Controlling `page breaks`_ (``page-break-*``, ``orphans``, ``widows``)
  * Conforming `font matching algorithm`_. Currently ``font-family``
    is directly passed to Pango.
  * `Bi-directional text`_. (May happen to kind of work in uninterrupted text
    thanks to Pango)

.. _PIL: http://www.pythonware.com/products/pil/
.. _CSS 3 Colors: http://www.w3.org/TR/css3-color/
.. _CSS 3 Selectors: http://www.w3.org/TR/css3-selectors/
.. _CSS 3 Paged Media: http://www.w3.org/TR/css3-page/
.. _box-sizing: http://www.w3.org/TR/css3-ui/#box-sizing
.. _Floats: http://www.w3.org/TR/CSS21/visuren.html#floats
.. _Absolute: http://www.w3.org/TR/CSS21/visuren.html#absolute-positioning
.. _fixed: http://www.w3.org/TR/CSS21/visuren.html#fixed-positioning
.. _z-index: http://www.w3.org/TR/CSS21/visuren.html#layers
.. _relative: http://www.w3.org/TR/CSS21/visuren.html#relative-positioning
.. _Automatic table layout: http://www.w3.org/TR/CSS21/tables.html#auto-table-layout
.. _Inline blocks: http://www.w3.org/TR/CSS21/visuren.html#value-def-inline-block
.. _border collapsing: http://www.w3.org/TR/CSS21/tables.html#collapsing-borders
.. _Collapsing margins: http://www.w3.org/TR/CSS21/box.html#collapsing-margins
.. _width: http://www.w3.org/TR/CSS21/visudet.html#min-max-widths
.. _height: http://www.w3.org/TR/CSS21/visudet.html#min-max-heights
.. _Overflow: http://www.w3.org/TR/CSS21/visufx.html#overflow-clipping
.. _Border styles: http://www.w3.org/TR/CSS21/box.html#border-style-properties
.. _Vertical align: http://www.w3.org/TR/CSS21/visudet.html#propdef-vertical-align
.. _Letter and word spacing: http://www.w3.org/TR/CSS21/text.html#spacing-props
.. _Justified text: http://www.w3.org/TR/CSS21/text.html#alignment-prop
.. _page breaks: http://www.w3.org/TR/CSS21/page.html#page-breaks
.. _font matching algorithm: http://www.w3.org/TR/CSS21/fonts.html#algorithm
.. _Bi-directional text: http://www.w3.org/TR/CSS21/visuren.html#direction
