Features
========

WeasyPrint 0.2 supports:

(For older versions, see the changelog_.)

.. _changelog: https://github.com/Kozea/WeasyPrint/blob/master/CHANGES

* Fetching and parsing HTML

  * Finding CSS stylesheets in ``<link rel="stylesheet">`` and ``<style>``
    elements
  * Raster images in ``<img>`` elements (files formats supported by PIL)

* CSS 3 Colors
* CSS 3 Selectors except ``:lang``, ``:first-line`` and
  ``:first-letter``
* Part of CSS 3 Paged Media: page size, borders, padding and margins
* ``box-sizing`` form CSS3 Basic User Interface
* All of CSS 2.1 except:

  * Floats
  * Absolute, fixed and relative positioning and z-index
  * Inline blocks
  * Automatic table layout and table border collapsing
  * Margin collapsing
  * Minimum and maximum width and height
  * Overflow and clip
  * Border styles ``double``, ``groove``, ``ridge``, ``inset`` and ``outset``
  * Vertical align ``top`` and ``bottom`` (they are interpreted as
    ``text-top`` and ``text-bottom``, respectively)
  * The ``:lang`` pseudo-class, ``:first-line`` and ``:first-letter``
    pseudo-elements
  * Generated content with the ``:before`` and ``:after`` pseudo-elements,
    including counters
  * Numbered / ordered lists
  * Letter and word spacing
  * Justified text
  * Controlling page breaks (``page-break-*``, ``orphans``, ``widows``)
  * Conforming font matching algorithm. Currently ``font-family`` is directly
    passed to Pango.
  * Bi-directional text. (May happen to kind of work in uninterrupted text
    thanks to Pango)
