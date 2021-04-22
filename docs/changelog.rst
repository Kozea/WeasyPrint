Changelog
=========


Version 53.0b1
--------------

Released on 2021-04-22.

**This version is experimental, don't use it in production. If you find bugs,
please report them!**

This version uses its own PDF generator instead of Cairo. Rendering may be
different for text, gradients, SVG images…

New features:

* `#1328 <https://github.com/Kozea/WeasyPrint/pull/1328>`_:
  Add ISO and JIS paper sizes
* `#1309 <https://github.com/Kozea/WeasyPrint/pull/1309>`_:
  Leader support, with financial support from Simonsoft

Bug fixes:

* `#504 <https://github.com/Kozea/WeasyPrint/issues/504>`_:
  Fix rendering bugs with PDF gradients
* `#606 <https://github.com/Kozea/WeasyPrint/issues/606>`_:
  Fix rounding errors on PDF dimensions
* `#1264 <https://github.com/Kozea/WeasyPrint/issues/1264>`_:
  Include witdh/height when calculating auto margins of absolute boxes
* `#1191 <https://github.com/Kozea/WeasyPrint/issues/1191>`_:
  Don’t try to get an earlier page break between columns
* `#1235 <https://github.com/Kozea/WeasyPrint/issues/1235>`_:
  Include padding, border, padding when calculating inline-block width
* `#1199 <https://github.com/Kozea/WeasyPrint/issues/1199>`_:
  Fix kerning issues with small fonts

Documentation:

* `#1298 <https://github.com/Kozea/WeasyPrint/pull/1298>`_:
  Rewrite documentation

Contributors:

* Guillaume Ayoub
* Lucie Anglade
* Felix Schwarz
* Syrus Dark
* Christoph Päper

Backers and sponsors:

* Simonsoft
* PDF Blocks
* Menutech
* Manuel Barkhau
* Simon Sapin
* Nathalie Gutton
* Andreas Zettl
* René Fritz
* Tom Pohl
* KontextWork
* Moritz Mahringer
* Florian Demmer
* Maykin Media
* Yanal-Yvez Fargialla
* Des images et des mots
* Yevhenii Hyzyla


Version 52.5
------------

Released on 2021-04-17.

Bug fixes:

* `#1336 <https://github.com/Kozea/WeasyPrint/issues/1336>`_:
  Fix text breaking exception
* `#1318 <https://github.com/Kozea/WeasyPrint/issues/1318>`_:
  Fix @font-face rules with Pango 1.48.3+

Contributors:

* Guillaume Ayoub

Backers and sponsors:

* Simonsoft
* PDF Blocks
* Menutech
* Manuel Barkhau
* Simon Sapin
* Nathalie Gutton
* Andreas Zettl
* René Fritz
* Tom Pohl
* KontextWork
* Moritz Mahringer
* Florian Demmer
* Maykin Media
* Yanal-Yvez Fargialla
* Des images et des mots
* Yevhenii Hyzyla


Version 52.4
------------

Released on 2021-03-11.

Bug fixes:

* `#1304 <https://github.com/Kozea/WeasyPrint/issues/1304>`_:
  Don’t try to draw SVG files with no size
* `ece5f066 <https://github.com/Kozea/WeasyPrint/commit/ece5f066>`_:
  Avoid crash on last word detection
* `4ee42e48 <https://github.com/Kozea/WeasyPrint/commit/4ee42e48>`_:
  Remove last word before ellipses when hyphenated

Contributors:

* Guillaume Ayoub

Backers and sponsors:

* PDF Blocks
* Simonsoft
* Menutech
* Simon Sapin
* Manuel Barkhau
* Andreas Zettl
* Nathalie Gutton
* Tom Pohl
* René Fritz
* Moritz Mahringer
* Florian Demmer
* KontextWork
* Michele Mostarda


Version 52.3
------------

Released on 2021-03-02.

Bug fixes:

* `#1299 <https://github.com/Kozea/WeasyPrint/issues/1299>`_:
  Fix imports with url() and quotes

New features:

* `#1300 <https://github.com/Kozea/WeasyPrint/pull/1300>`_:
  Add support of line-clamp, with financial support from
  expert Germany

Contributors:

* Guillaume Ayoub
* Lucie Anglade

Backers and sponsors:

* PDF Blocks
* Simonsoft
* Menutech
* Simon Sapin
* Manuel Barkhau
* Andreas Zettl
* Nathalie Gutton
* Tom Pohl
* Moritz Mahringer
* Florian Demmer
* KontextWork
* Michele Mostarda


Version 52.2
------------

Released on 2020-12-06.

Bug fixes:

* `238e214 <https://github.com/Kozea/WeasyPrint/commit/238e214>`_:
  Fix URL handling with tinycss2
* `#1248 <https://github.com/Kozea/WeasyPrint/issues/1248>`_:
  Include missing test data
* `#1254 <https://github.com/Kozea/WeasyPrint/issues/1254>`_:
  Top margins removed from children when tables are displayed on multiple pages
* `#1250 <https://github.com/Kozea/WeasyPrint/issues/1250>`_:
  Correctly draw borders on the last line of split tables
* `a6f9c80 <https://github.com/Kozea/WeasyPrint/commit/a6f9c80>`_:
  Add a nice gif to please gdk-pixbuf 2.42.0

Contributors:

* Guillaume Ayoub
* Lucie Anglade
* Felix Schwarz

Backers and sponsors:

* PDF Blocks
* Simonsoft
* Menutech
* Simon Sapin
* Nathalie Gutton
* Andreas Zetti
* Tom Pohl
* Florian Demmer
* Moritz Mahringer


Version 52.1
------------

Released on 2020-11-02.

Bug fixes:

* `238e214 <https://github.com/Kozea/WeasyPrint/commit/238e214>`_:
  Fix URL handling with tinycss2

Contributors:

* Guillaume Ayoub

Backers and sponsors:

* Simonsoft
* Simon Sapin
* Nathalie Gutton
* Andreas Zettl
* Florian Demmer
* Moritz Mahringer


Version 52
----------

Released on 2020-10-29.

Dependencies:

* Python 3.6+ is now needed, Python 3.5 is not supported anymore
* WeasyPrint now depends on Pillow

New features:

* `#1019 <https://github.com/Kozea/WeasyPrint/issues/1019>`_:
  Implement ``counter-set``
* `#1080 <https://github.com/Kozea/WeasyPrint/issues/1080>`_:
  Don’t display ``template`` tags
* `#1210 <https://github.com/Kozea/WeasyPrint/pull/1210>`_:
  Use ``download`` attribute in ``a`` tags for attachment's filename
* `#1206 <https://github.com/Kozea/WeasyPrint/issues/1206>`_:
  Handle strings in ``list-style-type``
* `#1165 <https://github.com/Kozea/WeasyPrint/pull/1165>`_:
  Add support for concatenating ``var()`` functions in ``content`` declarations
* `c56b96b <https://github.com/Kozea/WeasyPrint/commit/c56b96b>`_:
  Add an option to optimize embedded images size, with financial support from
  Hashbang
* `#969 <https://github.com/Kozea/WeasyPrint/issues/969>`_:
  Add an image cache that can be shared between documents, with financial
  support from Hashbang

Bug fixes:

* `#1141 <https://github.com/Kozea/WeasyPrint/pull/1141>`_:
  Don’t clip page margins on account of ``body`` overflow
* `#1000 <https://github.com/Kozea/WeasyPrint/issues/1000>`_:
  Don’t apply ``text-indent`` twice on inline blocks
* `#1051 <https://github.com/Kozea/WeasyPrint/issues/1051>`_:
  Avoid random line breaks
* `#1120 <https://github.com/Kozea/WeasyPrint/pull/1120>`_:
  Gather target counters in page margins
* `#1110 <https://github.com/Kozea/WeasyPrint/issues/1110>`_:
  Handle most cases for boxes avoiding floats in rtl containers, with financial
  support from Innovative Software
* `#1111 <https://github.com/Kozea/WeasyPrint/issues/1111>`_:
  Fix horizontal position of last rtl line, with financial support from
  Innovative Software
* `#1114 <https://github.com/Kozea/WeasyPrint/issues/1114>`_:
  Fix bug with transparent borders in tables
* `#1146 <https://github.com/Kozea/WeasyPrint/pull/1146>`_:
  Don’t gather bookmarks twice for blocks that are displayed on two pages
* `#1237 <https://github.com/Kozea/WeasyPrint/issues/1237>`_:
  Use fallback fonts on unsupported WOFF2 and WOFF fonts
* `#1025 <https://github.com/Kozea/WeasyPrint/issues/1025>`_:
  Don’t insert the same layout attributes multiple times
* `#1027 <https://github.com/Kozea/WeasyPrint/issues/1027>`_:
  Don’t try to break tables after the header or before the footer
* `#1050 <https://github.com/Kozea/WeasyPrint/issues/1050>`_:
  Don’t crash on absolute SVG files with no intrinsic size
* `#1204 <https://github.com/Kozea/WeasyPrint/issues/1204>`_:
  Fix a crash with a flexbox corner case
* `#1030 <https://github.com/Kozea/WeasyPrint/pull/1030>`_:
  Fix frozen builds
* `#1089 <https://github.com/Kozea/WeasyPrint/pull/1089>`_:
  Fix Pyinstaller builds
* `#1216 <https://github.com/Kozea/WeasyPrint/pull/1213>`_:
  Fix embedded files
* `#1225 <https://github.com/Kozea/WeasyPrint/pull/1225>`_:
  Initial support of RTL direction in flexbox layout

Documentation:

* `#1149 <https://github.com/Kozea/WeasyPrint/issues/1149>`_:
  Add the ``--quiet`` CLI option in the documentation
* `#1061 <https://github.com/Kozea/WeasyPrint/pull/1061>`_:
  Update install instructions on Windows

Tests:

* `#1209 <https://github.com/Kozea/WeasyPrint/pull/1209>`_:
  Use GitHub Actions instead of Travis

Contributors:

* Guillaume Ayoub
* Lucie Anglade
* Tontyna
* Mohammed Y. Alnajdi
* Mike Voets
* Bjarni Þórisson
* Balázs Dukai
* Bart Broere
* Endalkachew
* Felix Schwarz
* Julien Sanchez
* Konstantin Alekseev
* Nicolas Hart
* Nikolaus Schlemm
* Thomas J. Lampoltshammer
* mPyth
* nempoBu4
* saddy001

Backers and sponsors:

* Hashbang
* Innovative Software
* Screenbreak
* Simon Sapin
* Lisa Warshaw
* Nathalie Gutton
* Andreas Zettl
* Florian Demmer
* Moritz Mahringer


Version 51
----------

Released on 2019-12-23.

Dependencies:

* Pyphen 0.9.1+ is now needed

New features:

* `#882 <https://github.com/Kozea/WeasyPrint/pull/882>`_:
  Add support of ``element()`` and ``running()``
* `#972 <https://github.com/Kozea/WeasyPrint/pull/972>`_:
  Add HTML element to Box class
* `7a4d6f8 <https://github.com/Kozea/WeasyPrint/commit/7a4d6f8>`_:
  Support ``larger`` and ``smaller`` values for ``font-size``

Bug fixes:

* `#960 <https://github.com/Kozea/WeasyPrint/pull/960>`_:
  Fix how fonts used for macOS tests are installed
* `#956 <https://github.com/Kozea/WeasyPrint/pull/956>`_:
  Fix various crashes due to line breaking bugs
* `#983 <https://github.com/Kozea/WeasyPrint/issues/983>`_:
  Fix typo in variable name
* `#975 <https://github.com/Kozea/WeasyPrint/pull/975>`_:
  Don’t crash when ``string-set`` is set to ``none``
* `#998 <https://github.com/Kozea/WeasyPrint/pull/998>`_:
  Keep font attributes when text lines are modified
* `#1005 <https://github.com/Kozea/WeasyPrint/issues/1005>`_:
  Don’t let presentational hints add decorations on tables with no borders
* `#974 <https://github.com/Kozea/WeasyPrint/pull/974>`_:
  Don’t crash on improper ``var()`` values
* `#1012 <https://github.com/Kozea/WeasyPrint/pull/1012>`_:
  Fix rendering of header and footer for empty tables
* `#1013 <https://github.com/Kozea/WeasyPrint/issues/1013>`_:
  Avoid quadratic time relative to tree depth when setting page names

Contributors:

- Lucie Anglade
- Guillaume Ayoub
- Guillermo Bonvehí
- Holger Brunn
- Felix Schwarz
- Tontyna


Version 50
----------

Released on 2019-09-19.

New features:

* `#209 <https://github.com/Kozea/WeasyPrint/issues/209>`_:
  Make ``break-*`` properties work inside tables
* `#661 <https://github.com/Kozea/WeasyPrint/issues/661>`_:
  Make blocks with ``overflow: auto`` grow to include floating children

Bug fixes:

* `#945 <https://github.com/Kozea/WeasyPrint/issues/945>`_:
  Don't break pages between a list item and its marker
* `#727 <https://github.com/Kozea/WeasyPrint/issues/727>`_:
  Avoid tables lost between pages
* `#831 <https://github.com/Kozea/WeasyPrint/issues/831>`_:
  Ignore auto margins on flex containers
* `#923 <https://github.com/Kozea/WeasyPrint/issues/923>`_:
  Fix a couple of crashes when splitting a line twice
* `#896 <https://github.com/Kozea/WeasyPrint/issues/896>`_:
  Fix skip stack order when using a reverse flex direction

Contributors:

- Lucie Anglade
- Guillaume Ayoub


Version 49
----------

Released on 2019-09-11.

Performance:

* Speed and memory use have been largely improved.

New features:

* `#700 <https://github.com/Kozea/WeasyPrint/issues/700>`_:
  Handle ``::marker`` pseudo-selector
* `135dc06c <https://github.com/Kozea/WeasyPrint/commit/135dc06c>`_:
  Handle ``recto`` and ``verso`` parameters for page breaks
* `#907 <https://github.com/Kozea/WeasyPrint/pull/907>`_:
  Provide a clean way to build layout contexts

Bug fixes:

* `#937 <https://github.com/Kozea/WeasyPrint/issues/937>`_:
  Fix rendering of tables with empty lines and rowspans
* `#897 <https://github.com/Kozea/WeasyPrint/issues/897>`_:
  Don't crash when small columns are wrapped in absolute blocks
* `#913 <https://github.com/Kozea/WeasyPrint/issues/913>`_:
  Fix a test about gradient colors
* `#924 <https://github.com/Kozea/WeasyPrint/pull/924>`_:
  Fix title for document with attachments
* `#917 <https://github.com/Kozea/WeasyPrint/issues/917>`_:
  Fix tests with Pango 1.44
* `#919 <https://github.com/Kozea/WeasyPrint/issues/919>`_:
  Fix padding and margin management for column flex boxes
* `#901 <https://github.com/Kozea/WeasyPrint/issues/901>`_:
  Fix width of replaced boxes with no intrinsic width
* `#906 <https://github.com/Kozea/WeasyPrint/issues/906>`_:
  Don't respect table cell width when content doesn't fit
* `#927 <https://github.com/Kozea/WeasyPrint/pull/927>`_:
  Don't use deprecated ``logger.warn`` anymore
* `a8662794 <https://github.com/Kozea/WeasyPrint/commit/a8662794>`_:
  Fix margin collapsing between caption and table wrapper
* `87d9e84f <https://github.com/Kozea/WeasyPrint/commit/87d9e84f>`_:
  Avoid infinite loops when rendering columns
* `789b80e6 <https://github.com/Kozea/WeasyPrint/commit/789b80e6>`_:
  Only use in flow children to set columns height
* `615e298a <https://github.com/Kozea/WeasyPrint/commit/615e298a>`_:
  Don't include floating elements each time we try to render a column
* `48d8632e <https://github.com/Kozea/WeasyPrint/commit/48d8632e>`_:
  Avoid not in flow children to compute column height
* `e7c452ce <https://github.com/Kozea/WeasyPrint/commit/e7c452ce>`_:
  Fix collapsing margins for columns
* `fb0887cf <https://github.com/Kozea/WeasyPrint/commit/fb0887cf>`_:
  Fix crash when using currentColor in gradients
* `f66df067 <https://github.com/Kozea/WeasyPrint/commit/f66df067>`_:
  Don't crash when using ex units in word-spacing in letter-spacing
* `c790ff20 <https://github.com/Kozea/WeasyPrint/commit/c790ff20>`_:
  Don't crash when properties needing base URL use var functions
* `d63eac31 <https://github.com/Kozea/WeasyPrint/commit/d63eac31>`_:
  Don't crash with object-fit: non images with no intrinsic size

Documentation:

* `#900 <https://github.com/Kozea/WeasyPrint/issues/900>`_:
  Add documentation about semantic versioning
* `#692 <https://github.com/Kozea/WeasyPrint/issues/692>`_:
  Add a snippet about PDF magnification
* `#899 <https://github.com/Kozea/WeasyPrint/pull/899>`_:
  Add .NET wrapper link
* `#893 <https://github.com/Kozea/WeasyPrint/pull/893>`_:
  Fixed wrong nested list comprehension example
* `#902 <https://github.com/Kozea/WeasyPrint/pull/902>`_:
  Add ``state`` to the ``make_bookmark_tree`` documentation
* `#921 <https://github.com/Kozea/WeasyPrint/pull/921>`_:
  Fix typos in the documentation
* `#328 <https://github.com/Kozea/WeasyPrint/issues/328>`_:
  Add CSS sample for forms

Contributors:

- Lucie Anglade
- Guillaume Ayoub
- Raphael Gaschignard
- Stani
- Szmen
- Thomas Dexter
- Tontyna


Version 48
----------

Released on 2019-07-08.

Dependencies:

* CairoSVG 2.4.0+ is now needed

New features:

* `#891 <https://github.com/Kozea/WeasyPrint/pull/891>`_:
  Handle ``text-overflow``
* `#878 <https://github.com/Kozea/WeasyPrint/pull/878>`_:
  Handle ``column-span``
* `#855 <https://github.com/Kozea/WeasyPrint/pull/855>`_:
  Handle all the ``text-decoration`` features
* `#238 <https://github.com/Kozea/WeasyPrint/issues/238>`_:
  Don't repeat background images when it's not needed
* `#875 <https://github.com/Kozea/WeasyPrint/issues/875>`_:
  Handle ``object-fit`` and ``object-position``
* `#870 <https://github.com/Kozea/WeasyPrint/issues/870>`_:
  Handle ``bookmark-state``

Bug fixes:

* `#686 <https://github.com/Kozea/WeasyPrint/issues/686>`_:
  Fix column balance when children are not inline
* `#885 <https://github.com/Kozea/WeasyPrint/issues/885>`_:
  Actually use the content box to resolve flex items percentages
* `#867 <https://github.com/Kozea/WeasyPrint/issues/867>`_:
  Fix rendering of KaTeX output, including (1) set row baseline of tables when
  no cells are baseline-aligned, (2) set baseline for inline tables, (3) don't
  align lines larger than their parents, (4) force CairoSVG to respect image
  size defined by CSS.
* `#873 <https://github.com/Kozea/WeasyPrint/issues/873>`_:
  Set a minimum height for empty list elements with outside marker
* `#811 <https://github.com/Kozea/WeasyPrint/issues/811>`_:
  Don't use translations to align flex items
* `#851 <https://github.com/Kozea/WeasyPrint/issues/851>`_,
  `#860 <https://github.com/Kozea/WeasyPrint/issues/860>`_:
  Don't cut pages when content overflows a very little bit
* `#862 <https://github.com/Kozea/WeasyPrint/issues/862>`_:
  Don't crash when using UTC dates in metadata

Documentation:

* `#854 <https://github.com/Kozea/WeasyPrint/issues/854>`_:
  Add a "Tips & Tricks" section

Contributors:

- Gabriel Corona
- Guillaume Ayoub
- Manuel Barkhau
- Nathan de Maestri
- Lucie Anglade
- theopeek


Version 47
----------

Released on 2019-04-12.

New features:

* `#843 <https://github.com/Kozea/WeasyPrint/pull/843>`_:
  Handle CSS variables
* `#846 <https://github.com/Kozea/WeasyPrint/pull/846>`_:
  Handle ``:nth()`` page selector
* `#847 <https://github.com/Kozea/WeasyPrint/pull/847>`_:
  Allow users to use a custom SSL context for HTTP requests

Bug fixes:

* `#797 <https://github.com/Kozea/WeasyPrint/issues/797>`_:
  Fix underlined justified text
* `#836 <https://github.com/Kozea/WeasyPrint/issues/836>`_:
  Fix crash when flex items are replaced boxes
* `#835 <https://github.com/Kozea/WeasyPrint/issues/835>`_:
  Fix ``margin-break: auto``


Version 46
----------

Released on 2019-03-20.

New features:

* `#771 <https://github.com/Kozea/WeasyPrint/issues/771>`_:
  Handle ``box-decoration-break``
* `#115 <https://github.com/Kozea/WeasyPrint/issues/115>`_:
  Handle ``margin-break``
* `#821 <https://github.com/Kozea/WeasyPrint/issues/821>`_:
  Continuous integration includes tests on Windows

Bug fixes:

* `#765 <https://github.com/Kozea/WeasyPrint/issues/765>`_,
  `#754 <https://github.com/Kozea/WeasyPrint/issues/754>`_,
  `#800 <https://github.com/Kozea/WeasyPrint/issues/800>`_:
  Fix many crashes related to the flex layout
* `#783 <https://github.com/Kozea/WeasyPrint/issues/783>`_:
  Fix a couple of crashes with strange texts
* `#827 <https://github.com/Kozea/WeasyPrint/pull/827>`_:
  Named strings and counters are case-sensitive
* `#823 <https://github.com/Kozea/WeasyPrint/pull/823>`_:
  Shrink min/max-height/width according to box-sizing
* `#728 <https://github.com/Kozea/WeasyPrint/issues/728>`_,
  `#171 <https://github.com/Kozea/WeasyPrint/issues/171>`_:
  Don't crash when fixed boxes are nested
* `#610 <https://github.com/Kozea/WeasyPrint/issues/610>`_,
  `#828 <https://github.com/Kozea/WeasyPrint/issues/828>`_:
  Don't crash when preformatted text lines end with a space
* `#808 <https://github.com/Kozea/WeasyPrint/issues/808>`_,
  `#387 <https://github.com/Kozea/WeasyPrint/issues/387>`_:
  Fix position of some images
* `#813 <https://github.com/Kozea/WeasyPrint/issues/813>`_:
  Don't crash when long preformatted text lines end with ``\n``

Documentation:

* `#815 <https://github.com/Kozea/WeasyPrint/pull/815>`_:
  Add documentation about custom ``url_fetcher``


Version 45
----------

Released on 2019-02-20.

WeasyPrint now has a `code of conduct
<https://github.com/Kozea/WeasyPrint/blob/master/CODE_OF_CONDUCT.rst>`_.

A new website has been launched, with beautiful and useful graphs about speed
and memory use across versions: check `WeasyPerf
<https://kozea.github.io/WeasyPerf/index.html>`_.

Dependencies:

* Python 3.5+ is now needed, Python 3.4 is not supported anymore

Bug fixes:

* `#798 <https://github.com/Kozea/WeasyPrint/pull/798>`_:
  Prevent endless loop and index out of range in pagination
* `#767 <https://github.com/Kozea/WeasyPrint/issues/767>`_:
  Add a ``--quiet`` CLI parameter
* `#784 <https://github.com/Kozea/WeasyPrint/pull/784>`_:
  Fix library loading on Alpine
* `#791 <https://github.com/Kozea/WeasyPrint/pull/791>`_:
  Use path2url in tests for Windows
* `#789 <https://github.com/Kozea/WeasyPrint/pull/789>`_:
  Add LICENSE file to distributed sources
* `#788 <https://github.com/Kozea/WeasyPrint/pull/788>`_:
  Fix pending references
* `#780 <https://github.com/Kozea/WeasyPrint/issues/780>`_:
  Don't draw patterns for empty page backgrounds
* `#774 <https://github.com/Kozea/WeasyPrint/issues/774>`_:
  Don't crash when links include quotes
* `#637 <https://github.com/Kozea/WeasyPrint/issues/637>`_:
  Fix a problem with justified text
* `#763 <https://github.com/Kozea/WeasyPrint/pull/763>`_:
  Launch tests with Python 3.7
* `#704 <https://github.com/Kozea/WeasyPrint/issues/704>`_:
  Fix a corner case with tables
* `#804 <https://github.com/Kozea/WeasyPrint/pull/804>`_:
  Don't logger handlers defined before importing WeasyPrint
* `#109 <https://github.com/Kozea/WeasyPrint/issues/109>`_,
  `#748 <https://github.com/Kozea/WeasyPrint/issues/748>`_:
  Don't include punctuation for hyphenation
* `#770 <https://github.com/Kozea/WeasyPrint/issues/770>`_:
  Don't crash when people use uppercase words from old-fashioned Microsoft
  fonts in tables, especially when there's an 5th column
* Use a `separate logger
  <https://weasyprint.readthedocs.io/en/latest/tutorial.html#logging>`_ to
  report the rendering process
* Add a ``--debug`` CLI parameter and set debug level for unknown prefixed CSS
  properties
* Define minimal versions of Python and setuptools in setup.cfg

Documentation:

* `#796 <https://github.com/Kozea/WeasyPrint/pull/796>`_:
  Fix a small typo in the tutorial
* `#792 <https://github.com/Kozea/WeasyPrint/pull/792>`_:
  Document no alignement character support
* `#773 <https://github.com/Kozea/WeasyPrint/pull/773>`_:
  Fix phrasing in Hacking section
* `#402 <https://github.com/Kozea/WeasyPrint/issues/402>`_:
  Add a paragraph about fontconfig error
* `#764 <https://github.com/Kozea/WeasyPrint/pull/764>`_:
  Fix list of dependencies for Alpine
* Fix API documentation of HTML and CSS classes


Version 44
----------

Released on 2018-12-29.

Bug fixes:

* `#742 <https://github.com/Kozea/WeasyPrint/issues/742>`_:
  Don't crash during PDF generation when locale uses commas as decimal separator
* `#746 <https://github.com/Kozea/WeasyPrint/issues/746>`_:
  Close file when reading VERSION
* Improve speed and memory usage for long texts.

Documentation:

* `#733 <https://github.com/Kozea/WeasyPrint/pull/733>`_:
  Small documentation fixes
* `#735 <https://github.com/Kozea/WeasyPrint/pull/735>`_:
  Fix broken links in NEWS.rst


Version 43
----------

Released on 2018-11-09.

Bug fixes:

* `#726 <https://github.com/Kozea/WeasyPrint/issues/726>`_:
  Make empty strings clear previous values of named strings
* `#729 <https://github.com/Kozea/WeasyPrint/issues/729>`_:
  Include tools in packaging

This version also includes the changes from unstable rc1 and rc2 versions
listed below.


Version 43rc2
-------------

Released on 2018-11-02.

**This version is experimental, don't use it in production. If you find bugs,
please report them!**

Bug fixes:

* `#706 <https://github.com/Kozea/WeasyPrint/issues/706>`_:
  Fix text-indent at the beginning of a page
* `#687 <https://github.com/Kozea/WeasyPrint/issues/687>`_:
  Allow query strings in file:// URIs
* `#720 <https://github.com/Kozea/WeasyPrint/issues/720>`_:
  Optimize minimum size calculation of long inline elements
* `#717 <https://github.com/Kozea/WeasyPrint/issues/717>`_:
  Display <details> tags as blocks
* `#691 <https://github.com/Kozea/WeasyPrint/issues/691>`_:
  Don't recalculate max content widths when distributing extra space for tables
* `#722 <https://github.com/Kozea/WeasyPrint/issues/722>`_:
  Fix bookmarks and strings set on images
* `#723 <https://github.com/Kozea/WeasyPrint/issues/723>`_:
  Warn users when string() is not used in page margin


Version 43rc1
-------------

Released on 2018-10-15.

**This version is experimental, don't use it in production. If you find bugs,
please report them!**

Dependencies:

* Python 3.4+ is now needed, Python 2.x is not supported anymore
* Cairo 1.15.4+ is now needed, but 1.10+ should work with missing features
  (such as links, outlines and metadata)
* Pdfrw is not needed anymore

New features:

* `Beautiful website <https://weasyprint.org>`_
* `#579 <https://github.com/Kozea/WeasyPrint/issues/579>`_:
  Initial support of flexbox
* `#592 <https://github.com/Kozea/WeasyPrint/pull/592>`_:
  Support @font-face on Windows
* `#306 <https://github.com/Kozea/WeasyPrint/issues/306>`_:
  Add a timeout parameter to the URL fetcher functions
* `#594 <https://github.com/Kozea/WeasyPrint/pull/594>`_:
  Split tests using modern pytest features
* `#599 <https://github.com/Kozea/WeasyPrint/pull/599>`_:
  Make tests pass on Windows
* `#604 <https://github.com/Kozea/WeasyPrint/pull/604>`_:
  Handle target counters and target texts
* `#631 <https://github.com/Kozea/WeasyPrint/pull/631>`_:
  Enable counter-increment and counter-reset in page context
* `#622 <https://github.com/Kozea/WeasyPrint/issues/622>`_:
  Allow pathlib.Path objects for HTML, CSS and Attachment classes
* `#674 <https://github.com/Kozea/WeasyPrint/issues/674>`_:
  Add extensive installation instructions for Windows

Bug fixes:

* `#558 <https://github.com/Kozea/WeasyPrint/issues/558>`_:
  Fix attachments
* `#565 <https://github.com/Kozea/WeasyPrint/issues/565>`_,
  `#596 <https://github.com/Kozea/WeasyPrint/issues/596>`_,
  `#539 <https://github.com/Kozea/WeasyPrint/issues/539>`_:
  Fix many PDF rendering, printing and compatibility problems
* `#614 <https://github.com/Kozea/WeasyPrint/issues/614>`_:
  Avoid crashes and endless loops caused by a Pango bug
* `#662 <https://github.com/Kozea/WeasyPrint/pull/662>`_:
  Fix warnings and errors when generating documentation
* `#666 <https://github.com/Kozea/WeasyPrint/issues/666>`_,
  `#685 <https://github.com/Kozea/WeasyPrint/issues/685>`_:
  Fix many table layout rendering problems
* `#680 <https://github.com/Kozea/WeasyPrint/pull/680>`_:
  Don't crash when there's no font available
* `#662 <https://github.com/Kozea/WeasyPrint/pull/662>`_:
  Fix support of some align values in tables


Version 0.42.3
--------------

Released on 2018-03-27.

Bug fixes:

* `#583 <https://github.com/Kozea/WeasyPrint/issues/583>`_:
  Fix floating-point number error to fix floating box layout
* `#586 <https://github.com/Kozea/WeasyPrint/issues/586>`_:
  Don't optimize resume_at when splitting lines with trailing spaces
* `#582 <https://github.com/Kozea/WeasyPrint/issues/582>`_:
  Fix table layout with no overflow
* `#580 <https://github.com/Kozea/WeasyPrint/issues/580>`_:
  Fix inline box breaking function
* `#576 <https://github.com/Kozea/WeasyPrint/issues/576>`_:
  Split replaced_min_content_width and replaced_max_content_width
* `#574 <https://github.com/Kozea/WeasyPrint/issues/574>`_:
  Respect text direction and don't translate rtl columns twice
* `#569 <https://github.com/Kozea/WeasyPrint/issues/569>`_:
  Get only first line's width of inline children to get linebox width


Version 0.42.2
--------------

Released on 2018-02-04.

Bug fixes:

* `#560 <https://github.com/Kozea/WeasyPrint/issues/560>`_:
  Fix a couple of crashes and endless loops when breaking lines.


Version 0.42.1
--------------

Released on 2018-02-01.

Bug fixes:

* `#566 <https://github.com/Kozea/WeasyPrint/issues/566>`_:
  Don't crash when using @font-config.
* `#567 <https://github.com/Kozea/WeasyPrint/issues/567>`_:
  Fix text-indent with text-align: justify.
* `#465 <https://github.com/Kozea/WeasyPrint/issues/465>`_:
  Fix string(\*, start).
* `#562 <https://github.com/Kozea/WeasyPrint/issues/562>`_:
  Handle named pages with pseudo-class.
* `#507 <https://github.com/Kozea/WeasyPrint/issues/507>`_:
  Fix running headers.
* `#557 <https://github.com/Kozea/WeasyPrint/issues/557>`_:
  Avoid infinite loops in inline_line_width.
* `#555 <https://github.com/Kozea/WeasyPrint/issues/555>`_:
  Fix margins, borders and padding in column layouts.


Version 0.42
------------

Released on 2017-12-26.

WeasyPrint is not tested with (end-of-life) Python 3.3 anymore.

**This release is probably the last version of the 0.x series.**

Next version may include big changes:

- end of Python 2.7 support,
- initial support of bidirectional text,
- initial support of flexbox,
- improvements for speed and memory usage.

New features:

* `#532 <https://github.com/Kozea/WeasyPrint/issues/532>`_:
  Support relative file URIs when using CLI.

Bug fixes:

* `#553 <https://github.com/Kozea/WeasyPrint/issues/553>`_:
  Fix slow performance for pre-formatted boxes with a lot of children.
* `#409 <https://github.com/Kozea/WeasyPrint/issues/409>`_:
  Don't crash when rendering some tables.
* `#39 <https://github.com/Kozea/WeasyPrint/issues/39>`_:
  Fix rendering of floats in inlines.
* `#301 <https://github.com/Kozea/WeasyPrint/issues/301>`_:
  Split lines carefully.
* `#530 <https://github.com/Kozea/WeasyPrint/issues/530>`_:
  Fix root when frozen with Pyinstaller.
* `#534 <https://github.com/Kozea/WeasyPrint/issues/534>`_:
  Handle SVGs containing images embedded as data URIs.
* `#360 <https://github.com/Kozea/WeasyPrint/issues/360>`_:
  Fix border-radius rendering problem with some PDF readers.
* `#525 <https://github.com/Kozea/WeasyPrint/issues/525>`_:
  Fix pipenv support.
* `#227 <https://github.com/Kozea/WeasyPrint/issues/227>`_:
  Smartly handle replaced boxes with percentage width in auto-width parents.
* `#520 <https://github.com/Kozea/WeasyPrint/issues/520>`_:
  Don't ignore CSS @page rules that are imported by an @import rule.


Version 0.41
------------

Released on 2017-10-05.

WeasyPrint now depends on pdfrw >= 0.4.

New features:

* `#471 <https://github.com/Kozea/WeasyPrint/issues/471>`_:
  Support page marks and bleed.

Bug fixes:

* `#513 <https://github.com/Kozea/WeasyPrint/issues/513>`_:
  Don't crash on unsupported image-resolution values.
* `#506 <https://github.com/Kozea/WeasyPrint/issues/506>`_:
  Fix @font-face use with write_* methods.
* `#500 <https://github.com/Kozea/WeasyPrint/pull/500>`_:
  Improve readability of _select_source function.
* `#498 <https://github.com/Kozea/WeasyPrint/issues/498>`_:
  Use CSS prefixes as recommanded by the CSSWG.
* `#441 <https://github.com/Kozea/WeasyPrint/issues/441>`_:
  Fix rendering problems and crashes when using @font-face.
* `bb3a4db <https://github.com/Kozea/WeasyPrint/commit/bb3a4db>`_:
  Try to break pages after a block before trying to break inside it.
* `1d1654c <https://github.com/Kozea/WeasyPrint/commit/1d1654c>`_:
  Fix and test corner cases about named pages.

Documentation:

* `#508 <https://github.com/Kozea/WeasyPrint/pull/508>`_:
  Add missing libpangocairo dependency for Debian and Ubuntu.
* `a7b17fb <https://github.com/Kozea/WeasyPrint/commit/a7b17fb>`_:
  Add documentation on logged rendering steps.


Version 0.40
------------

Released on 2017-08-17.

WeasyPrint now depends on cssselect2 instead of cssselect and lxml.

New features:

* `#57 <https://github.com/Kozea/WeasyPrint/issues/57>`_:
  Named pages.
* Unprefix properties, see
  `#498 <https://github.com/Kozea/WeasyPrint/issues/498>`_.
* Add a "verbose" option logging the document generation steps.

Bug fixes:

* `#483 <https://github.com/Kozea/WeasyPrint/issues/483>`_:
  Fix slow performance with long pre-formatted texts.
* `#70 <https://github.com/Kozea/WeasyPrint/issues/70>`_:
  Improve speed and memory usage for long documents.
* `#487 <https://github.com/Kozea/WeasyPrint/issues/487>`_:
  Don't crash on local() fonts with a space and no quotes.


Version 0.39
------------

Released on 2017-06-24.

Bug fixes:

* Fix the use of WeasyPrint's URL fetcher with CairoSVG.


Version 0.38
------------

Released on 2017-06-16.

Bug fixes:

* `#477 <https://github.com/Kozea/WeasyPrint/issues/477>`_:
  Don't crash on font-face's src attributes with local functions.


Version 0.37
------------

Released on 2017-06-15.

WeasyPrint now depends on tinycss2 instead of tinycss.

New features:

* `#437 <https://github.com/Kozea/WeasyPrint/issues/437>`_:
  Support local links in generated PDFs.

Bug fixes:

* `#412 <https://github.com/Kozea/WeasyPrint/issues/412>`_:
  Use a NullHandler log handler when WeasyPrint is used as a library.
* `#417 <https://github.com/Kozea/WeasyPrint/issues/417>`_,
  `#472 <https://github.com/Kozea/WeasyPrint/issues/472>`_:
  Don't crash on some line breaks.
* `#327 <https://github.com/Kozea/WeasyPrint/issues/327>`_:
  Don't crash with replaced elements with height set in percentages.
* `#467 <https://github.com/Kozea/WeasyPrint/issues/467>`_:
  Remove incorrect line breaks.
* `#446 <https://github.com/Kozea/WeasyPrint/pull/446>`_:
  Let the logging module do the string interpolation.


Version 0.36
------------

Released on 2017-02-25.

New features:

* `#407 <https://github.com/Kozea/WeasyPrint/pull/407>`_:
  Handle ::first-letter.
* `#423 <https://github.com/Kozea/WeasyPrint/pull/423>`_:
  Warn user about broken cairo versions.

Bug fixes:

* `#411 <https://github.com/Kozea/WeasyPrint/pull/411>`_:
  Typos fixed in command-line help.


Version 0.35
------------

Released on 2017-02-25.

Bug fixes:

* `#410 <https://github.com/Kozea/WeasyPrint/pull/410>`_:
  Fix AssertionError in split_text_box.


Version 0.34
------------

Released on 2016-12-21.

Bug fixes:

* `#398 <https://github.com/Kozea/WeasyPrint/issues/398>`_:
  Honor the presentational_hints option for PDFs.
* `#399 <https://github.com/Kozea/WeasyPrint/pull/399>`_:
  Avoid CairoSVG-2.0.0rc* on Python 2.
* `#396 <https://github.com/Kozea/WeasyPrint/issues/396>`_:
  Correctly close files open by mkstemp.
* `#403 <https://github.com/Kozea/WeasyPrint/issues/403>`_:
  Cast the number of columns into int.
* Fix multi-page multi-columns and add related tests.


Version 0.33
------------

Released on 2016-11-28.

New features:

* `#393 <https://github.com/Kozea/WeasyPrint/issues/393>`_:
  Add tests on MacOS.
* `#370 <https://github.com/Kozea/WeasyPrint/issues/370>`_:
  Enable @font-face on MacOS.

Bug fixes:

* `#389 <https://github.com/Kozea/WeasyPrint/issues/389>`_:
  Always update resume_at when splitting lines.
* `#394 <https://github.com/Kozea/WeasyPrint/issues/394>`_:
  Don't build universal wheels.
* `#388 <https://github.com/Kozea/WeasyPrint/issues/388>`_:
  Fix logic when finishing block formatting context.


Version 0.32
------------

Released on 2016-11-17.

New features:

* `#28 <https://github.com/Kozea/WeasyPrint/issues/28>`_:
  Support @font-face on Linux.
* Support CSS fonts level 3 almost entirely, including OpenType features.
* `#253 <https://github.com/Kozea/WeasyPrint/issues/253>`_:
  Support presentational hints (optional).
* Support break-after, break-before and break-inside for pages and columns.
* `#384 <https://github.com/Kozea/WeasyPrint/issues/384>`_:
  Major performance boost.

Bux fixes:

* `#368 <https://github.com/Kozea/WeasyPrint/issues/368>`_:
  Respect white-space for shrink-to-fit.
* `#382 <https://github.com/Kozea/WeasyPrint/issues/382>`_:
  Fix the preferred width for column groups.
* Handle relative boxes in column-layout boxes.

Documentation:

* Add more and more documentation about Windows installation.
* `#355 <https://github.com/Kozea/WeasyPrint/issues/355>`_:
  Add fonts requirements for tests.


Version 0.31
------------

Released on 2016-08-28.

New features:

* `#124 <https://github.com/Kozea/WeasyPrint/issues/124>`_:
  Add MIME sniffing for images.
* `#60 <https://github.com/Kozea/WeasyPrint/issues/60>`_:
  CSS Multi-column Layout.
* `#197 <https://github.com/Kozea/WeasyPrint/pull/197>`_:
  Add hyphens at line breaks activated by a soft hyphen.

Bux fixes:

* `#132 <https://github.com/Kozea/WeasyPrint/pull/132>`_:
  Fix Python 3 compatibility on Windows.

Documentation:

* `#329 <https://github.com/Kozea/WeasyPrint/issues/329>`_:
  Add documentation about installation on Windows.


Version 0.30
------------

Released on 2016-07-18.

WeasyPrint now depends on html5lib-0.999999999.

Bux fixes:

* Fix Acid2
* `#325 <https://github.com/Kozea/WeasyPrint/issues/325>`_:
  Cutting lines is broken in page margin boxes.
* `#334 <https://github.com/Kozea/WeasyPrint/issues/334>`_:
  Newest html5lib 0.999999999 breaks rendering.


Version 0.29
------------

Released on 2016-06-17.

Bug fixes:

* `#263 <https://github.com/Kozea/WeasyPrint/pull/263>`_:
  Don't crash with floats with percents in positions.
* `#323 <https://github.com/Kozea/WeasyPrint/pull/323>`_:
  Fix CairoSVG 2.0 pre-release dependency in Python 2.x.


Version 0.28
------------

Released on 2016-05-16.

Bug fixes:

* `#189 <https://github.com/Kozea/WeasyPrint/issues/189>`_:
  ``white-space: nowrap`` still wraps on hyphens
* `#305 <https://github.com/Kozea/WeasyPrint/issues/305>`_:
  Fix crashes on some tables
* Don't crash when transform matrix isn't invertible
* Don't crash when rendering ratio-only SVG images
* Fix margins and borders on some tables


Version 0.27
------------

Released on 2016-04-08.

New features:

* `#295 <https://github.com/Kozea/WeasyPrint/pull/295>`_:
  Support the 'rem' unit.
* `#299 <https://github.com/Kozea/WeasyPrint/pull/299>`_:
  Enhance the support of SVG images.

Bug fixes:

* `#307 <https://github.com/Kozea/WeasyPrint/issues/307>`_:
  Fix the layout of cells larger than their tables.

Documentation:

* The website is now on GitHub Pages, the documentation is on Read the Docs.
* `#297 <https://github.com/Kozea/WeasyPrint/issues/297>`_:
  Rewrite the CSS chapter of the documentation.


Version 0.26
------------

Released on 2016-01-29.

New features:

* Support the `empty-cells` attribute.
* Respect table, column and cell widths.

Bug fixes:

* `#172 <https://github.com/Kozea/WeasyPrint/issues/172>`_:
  Unable to set table column width on tables td's.
* `#151 <https://github.com/Kozea/WeasyPrint/issues/151>`_:
  Table background colour bleeds beyond table cell boundaries.
* `#260 <https://github.com/Kozea/WeasyPrint/issues/260>`_:
  TypeError: unsupported operand type(s) for +: 'float' and 'str'.
* `#288 <https://github.com/Kozea/WeasyPrint/issues/288>`_:
  Unwanted line-breaks in bold text.
* `#286 <https://github.com/Kozea/WeasyPrint/issues/286>`_:
  AttributeError: 'Namespace' object has no attribute 'attachments'.


Version 0.25
------------

Released on 2015-12-17.

New features:

* Support the 'q' unit.

Bug fixes:

* `#285 <https://github.com/Kozea/WeasyPrint/issues/285>`_:
  Fix a crash happening when splitting lines.
* `#284 <https://github.com/Kozea/WeasyPrint/issues/284>`_:
  Escape parenthesis in PDF links.
* `#280 <https://github.com/Kozea/WeasyPrint/pull/280>`_:
  Replace utf8 with utf-8 for gettext/django compatibility.
* `#269 <https://github.com/Kozea/WeasyPrint/pull/269>`_:
  Add support for use when frozen.
* `#250 <https://github.com/Kozea/WeasyPrint/issues/250>`_:
  Don't crash when attachments are not available.


Version 0.24
------------

Released on 2015-08-04.

New features:

* `#174 <https://github.com/Kozea/WeasyPrint/issues/174>`_:
  Basic support for Named strings.

Bug fixes:

* `#207 <https://github.com/Kozea/WeasyPrint/issues/207>`_:
  Draw rounded corners on replaced boxes.
* `#224 <https://github.com/Kozea/WeasyPrint/pull/224>`_:
  Rely on the font size for rounding bug workaround.
* `#31 <https://github.com/Kozea/WeasyPrint/issues/31>`_:
  Honor the vertical-align property in fixed-height cells.
* `#202 <https://github.com/Kozea/WeasyPrint/issues/202>`_:
  Remove unreachable area/border at bottom of page.
* `#225 <https://github.com/Kozea/WeasyPrint/issues/225>`_:
  Don't allow unknown units during line-height validation.
* Fix some wrong conflict resolutions for table borders with inset
  and outset styles.


Version 0.23
------------

Released on 2014-09-16.

Bug fixes:

* `#196 <https://github.com/Kozea/WeasyPrint/issues/196>`_:
  Use the default image sizing algorithm for images’s preferred size.
* `#194 <https://github.com/Kozea/WeasyPrint/pull/194>`_:
  Try more library aliases with ``dlopen()``.
* `#201 <https://github.com/Kozea/WeasyPrint/pull/201>`_:
  Consider ``page-break-after-avoid`` when pushing floats to the next page.
* `#217 <https://github.com/Kozea/WeasyPrint/issues/217>`_:
  Avoid a crash on zero-sized background images.

Release process:

* Start testing on Python 3.4 on Travis-CI.


Version 0.22
------------

Released on 2014-05-05.

New features:

* `#86 <https://github.com/Kozea/WeasyPrint/pull/86>`_:
  Support gzip and deflate encoding in HTTP responses
* `#177 <https://github.com/Kozea/WeasyPrint/pull/177>`_:
  Support for PDF attachments.

Bug fixes:

* `#169 <https://github.com/Kozea/WeasyPrint/issues/169>`_:
  Fix a crash on percentage-width columns in an auto-width table.
* `#168 <https://github.com/Kozea/WeasyPrint/issues/168>`_:
  Make ``<fieldset>`` a block in the user-agent stylesheet.
* `#175 <https://github.com/Kozea/WeasyPrint/issues/175>`_:
  Fix some ``dlopen()`` library loading issues on OS X.
* `#183 <https://github.com/Kozea/WeasyPrint/issues/183>`_:
  Break to the next page before a float that would overflow the page.
  (It might still overflow if it’s bigger than the page.)
* `#188 <https://github.com/Kozea/WeasyPrint/issues/188>`_:
  Require a recent enough version of Pyphen

Release process:

* Drop Python 3.1 support.
* Set up [Travis CI](http://travis-ci.org/)
  to automatically test all pushes and pull requests.
* Start testing on Python 3.4 locally. (Travis does not support 3.4 yet.)


Version 0.21
------------

Released on 2014-01-11.

New features:

* Add the `overflow-wrap <http://dev.w3.org/csswg/css-text/#overflow-wrap>`_
  property, allowing line breaks inside otherwise-unbreakable words.
  Thanks Frédérick Deslandes!
* Add the `image-resolution
  <http://dev.w3.org/csswg/css-images-3/#the-image-resolution>`_ property,
  allowing images to be sized proportionally to their intrinsic size
  at a resolution other than 96 image pixels per CSS ``in``
  (ie. one image pixel per CSS ``px``)

Bug fixes:

* `#145 <https://github.com/Kozea/WeasyPrint/issues/145>`_:
  Fix parsing HTML from an HTTP URL on Python 3.x
* `#40 <https://github.com/Kozea/WeasyPrint/issues/40>`_:
  Use more general hyphenation dictionnaries for specific document languages.
  (E.g. use ``hyph_fr.dic`` for ``lang="fr_FR"``.)
* `#26 <https://github.com/Kozea/WeasyPrint/issues/26>`_:
  Fix ``min-width`` and ``max-width`` on floats.
* `#100 <https://github.com/Kozea/WeasyPrint/issues/100>`_:
  Fix a crash on trailing whitespace with ``font-size: 0``
* `#82 <https://github.com/Kozea/WeasyPrint/issues/82>`_:
  Borders on tables with ``border-collapse: collapse`` were sometimes
  drawn at an incorrect position.
* `#30 <https://github.com/Kozea/WeasyPrint/issues/30>`_:
  Fix positioning of images with ``position: absolute``.
* `#118 <https://github.com/Kozea/WeasyPrint/issues/118>`_:
  Fix a crash when using ``position: absolute``
  inside a ``position: relative`` element.
* Fix ``visibility: collapse`` to behave like ``visibility: hidden``
  on elements other than table rows and table columns.
* `#147 <https://github.com/Kozea/WeasyPrint/issues/147>`_ and
  `#153 <https://github.com/Kozea/WeasyPrint/issues/153>`_:
  Fix dependencies to require lxml 3.0 or a more recent version.
  Thanks gizmonerd and Thomas Grainger!
* `#152 <https://github.com/Kozea/WeasyPrint/issues/152>`_:
  Fix a crash on percentage-sized table cells in auto-sized tables.
  Thanks Johannes Duschl!


Version 0.20.2
--------------

Released on 2013-12-18.

* Fix `#146 <https://github.com/Kozea/WeasyPrint/issues/146>`_: don't crash
  when drawing really small boxes with dotted/dashed borders


Version 0.20.1
--------------

Released on 2013-12-16.

* Depend on html5lib >= 0.99 instead of 1.0b3 to fix pip 1.4 support.
* Fix `#74 <https://github.com/Kozea/WeasyPrint/issues/74>`_: don't crash on
  space followed by dot at line break.
* Fix `#78 <https://github.com/Kozea/WeasyPrint/issues/78>`_: nicer colors for
  border-style: ridge/groove/inset/outset.


Version 0.20
------------

Released on 2013-12-14.

* Add support for ``border-radius``.
* Feature `#77 <https://github.com/Kozea/WeasyPrint/issues/77>`_: Add PDF
  metadata from HTML.
* Feature `#12 <https://github.com/Kozea/WeasyPrint/pull/12>`_: Use html5lib.
* Tables: handle percentages for column groups, columns and cells, and values
  for row height.
* Bug fixes:

  * Fix `#84 <https://github.com/Kozea/WeasyPrint/pull/84>`_: don't crash when
    stylesheets are not available.
  * Fix `#101 <https://github.com/Kozea/WeasyPrint/issues/101>`_: use page ids
    instead of page numbers in PDF bookmarks.
  * Use ``logger.warning`` instead of deprecated ``logger.warn``.
  * Add 'font-stretch' in the 'font' shorthand.


Version 0.19.2
--------------

Released on 2013-06-18.

Bug fix release:

* Fix `#88 <https://github.com/Kozea/WeasyPrint/issues/88>`_:
  ``text-decoration: overline`` not being drawn above the text
* Bug fix: Actually draw multiple lines when multiple values are given
  to ``text-decoration``.
* Use the font metrics for text decoration positioning.
* Bug fix: Don't clip the border with ``overflow: hidden``.
* Fix `#99 <https://github.com/Kozea/WeasyPrint/issues/99>`_:
  Regression: JPEG images not loading with cairo 1.8.x.


Version 0.19.1
--------------

Released on 2013-04-30.

Bug fix release:

* Fix incorrect intrinsic width calculation
  leading to unnecessary line breaks in floats, tables, etc.
* Tweak border painting to look better
* Fix unnecessary page break before big tables.
* Fix table row overflowing at the bottom of the page
  when there are margins above the table.
* Fix ``position: fixed`` to actually repeat on every page.
* Fix `#76 <https://github.com/Kozea/WeasyPrint/issues/76>`_:
  repeat ``<thead>`` and ``<tfoot>`` elements on every page,
  even with table border collapsing.


Version 0.19
------------

Released on 2013-04-18.

* Add support for ``linear-gradient()`` and ``radial-gradient``
  in background images.
* Add support for the ``ex`` and ``ch`` length units.
  (``1ex`` is based on the font instead of being always ``0.5em`` as before.)
* Add experimental support for Level 4 hyphenation properties.
* Drop support for CFFI < 0.6 and cairocffi < 0.4.
* Many bug fixes, including:

 * Fix `#54 <https://github.com/Kozea/WeasyPrint/issues/54>`_:
   min/max-width/height on block-level images.
 * Fix `#71 <https://github.com/Kozea/WeasyPrint/issues/71>`_:
   Crash when parsing nested functional notation.


Version 0.18
------------

Released on 2013-03-30.

* Add support for Level 3 backgrounds,
  including multiple background layers per element/box.
* Forward-compatibility with (future releases of) cairocffi 0.4+ and CFFI 0.6+.
* Bug fixes:

  * Avoid some unnecessary line breaks
    for elements sized based on their content (aka. “shrink-to-fit”)
    such as floats and page headers.
  * Allow page breaks between empty blocks.
  * Fix `#66 <https://github.com/Kozea/WeasyPrint/issues/66>`_:
    Resolve images’ auto width from non-auto height and intrinsic ratio.
  * Fix `#21 <https://github.com/Kozea/WeasyPrint/issues/21>`_:
    The ``data:`` URL scheme is case-insensitive.
  * Fix `#53 <https://github.com/Kozea/WeasyPrint/issues/53>`_:
    Crash when backtracking for ``break-before/after: avoid``.


Version 0.17.1
--------------

Released on 2013-03-18.

Bug fixes:

* Fix `#41 <https://github.com/Kozea/WeasyPrint/issues/41>`_:
  GObject initialization when GDK-PixBuf is not installed.
* Fix `#42 <https://github.com/Kozea/WeasyPrint/issues/42>`_:
  absolute URLs without a base URL (ie. document parsed from a string.)
* Fix some whitespace collapsing bugs.
* Fix absolutely-positioned elements inside inline elements.
* Fix URL escaping of image references from CSS.
* Fix `#49 <https://github.com/Kozea/WeasyPrint/issues/49>`_:
  Division by 0 on dashed or dotted border smaller than one dot/dash.
* Fix `#44 <https://github.com/Kozea/WeasyPrint/issues/44>`_:
  bad interaction of ``page-break-before/after: avoid`` and floats.


Version 0.17
------------

Released on 2013-02-27.

* Added `text hyphenation`_ with the ``-weasy-hyphens`` property.
* When a document includes JPEG images, embed them as JPEG in the PDF output.
  This often results in smaller PDF file size
  compared to the default *deflate* compression.
* Switched to using CFFI instead of PyGTK or PyGObject-introspection.
* Layout bug fixes:

  - Correctly trim whitespace at the end of lines.
  - Fix some cases with floats within inline content.

.. _text hyphenation: https://weasyprint.readthedocs.io/en/latest/features.html#css-text-module-level-3-4


Version 0.16
------------

Released on 2012-12-13.

* Add the ``zoom`` parameter to ``HTML.write_pdf`` and
  ``Document.write_pdf() <weasyprint.document.Document.write_pdf>``
* Fix compatibility with old (and buggy) pycairo versions.
  WeasyPrint is now tested on 1.8.8 in addition to the latest.
* Fix layout bugs related to line trailing spaces.


Version 0.15
------------

Released on 2012-10-09.

* Add a low-level API that enables painting pages individually on any
  cairo surface.
* **Backward-incompatible change**: remove the ``HTML.get_png_pages``
  method. The new low-level API covers this functionality and more.
* Add support for the ``font-stretch`` property.
* Add support for ``@page:blank`` to select blank pages.
* New Sphinx-based and improved docs
* Bug fixes:

  - Importing Pango in some PyGTK installations.
  - Layout of inline-blocks with `vertical-align: top` or `bottom`.
  - Do not repeat a block’s margin-top or padding-top after a page break.
  - Performance problem with large tables split across many pages.
  - Anchors and hyperlinks areas now follow CSS transforms.
    Since PDF links have to be axis-aligned rectangles, the bounding box
    is used. This may be larger than expected with rotations that are
    not a multiple of 90 degrees.


Version 0.14
------------

Released on 2012-08-03.

* Add a public API to choose media type used for @media.
  (It still defaults to ``print``). Thanks Chung Lu!
* Add ``--base-url`` and ``--resolution`` to the command-line API, making it
  as complete as the Python one.
* Add support for the ``<base href="...">`` element in HTML.
* Add support for CSS outlines
* Switch to gdk-pixbuf instead of Pystacia for loading raster images.
* Bug fixes:

  - Handling of filenames and URLs on Windows
  - Unicode filenames with older version of py2cairo
  - ``base_url`` now behaves as expected when set to a directory name.
  - Make some tests more robust


Version 0.13
------------

Released on 2012-07-23.

* Add support for PyGTK, as an alternative to PyGObject + introspection.
  This should make WeasyPrint easier to run on platforms that not not have
  packages for PyGObject 3.x yet.
* Bug fix: crash in PDF outlines for some malformed HTML documents


Version 0.12
------------

Released on 2012-07-19.

* Add support for collapsed borders on tables. This is currently incompatible
  with repeating header and footer row groups on each page: headers and footers
  are treated as normal row groups on table with ``border-collapse: collapse``.
* Add ``url_fetcher`` to the public API. This enables users to hook into
  WeasyPrint for fetching linked stylesheets or images, eg. to generate them
  on the fly without going through the network.
  This enables the creation of `Flask-WeasyPrint
  <http://packages.python.org/Flask-WeasyPrint/>`_.


Version 0.11
------------

Released on 2012-07-04.

* Add support for floats and clear.
  Together with various bug fixes, this enables WeasyPrint to pass the Acid2
  test! Acid2 is now part of our automated test suite.
* Add support for the width, min-width, max-width, height, min-height and
  max-height properties in @page. The size property is now the size of the
  page’s containing block.
* Switch the Variable Dimension rules to `the new proposal
  <https://github.com/SimonSapin/css/blob/master/margin-boxes-variable-dimension>`_.
  The previous implementation was broken in many cases.
* The ``image-rendering``, ``transform``, ``transform-origin`` and ``size``
  properties are now unprefixed. The prefixed form (eg. -weasy-size) is ignored
  but gives a specific warning.


Version 0.10
------------

Released on 2012-06-25.

* Add ``get_png_pages()`` to the public API. It returns each page as
  a separate PNG image.
* Add a ``resolution`` parameter for PNG.
* Add *WeasyPrint Navigator*, a web application that shows WeasyPrint’s
  output with clickable links. Yes, that’s a browser in your browser.
  Start it with ``python -m weasyprint.navigator``
* Add support for `vertical-align: top` and `vertical-align: bottom`
* Add support for `page-break-before: avoid` and `page-break-after: avoid`
* Bug fixes


Version 0.9
-----------

Released on 2012-06-04.

* Relative, absolute and fixed positioning
* Proper painting order (z-index)
* In PDF: support for internal and external hyperlinks as well as bookmarks.
* Added the ``tree`` parameter to the ``HTML`` class: accepts a parsed lxml
  object.
* Bug fixes, including many crashes.

Bookmarks can be controlled by the ``-weasy-bookmark-level`` and
``-weasy-bookmark-label`` properties, as described in `CSS Generated Content
for Paged Media Module <http://dev.w3.org/csswg/css3-gcpm/#bookmarks>`_.

The default UA stylesheet sets a matching bookmark level on all ``<h1>``
to ``<h6>`` elements.


Version 0.8
-----------

Released on 2012-05-07.

* Switch from cssutils to tinycss_ as the CSS parser.
* Switch to the new cssselect_, almost all level 3 selectors are supported now.
* Support for inline blocks and inline tables
* Automatic table layout (column widths)
* Support for the ``min-width``, ``max-width``, ``min-height`` and
  ``max-height`` properties, except on table-related and page-related boxes.
* Speed improvements on big stylesheets / small documents thanks to tinycss.
* Many bug fixes

.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/


Version 0.7.1
-------------

Released on 2012-03-21.

Change the license from AGPL to BSD.


Version 0.7
-----------

Released on 2012-03-21.

* Support page breaks between table rows
* Support for the ``orphans`` and ``widows`` properties.
* Support for ``page-break-inside: avoid``
* Bug fixes

Only avoiding page breaks before/after an element is still missing.


Version 0.6.1
-------------

Released on 2012-03-01.

Fix a packaging bug. (Remove use_2to3 in setup.py. We use the same
codebase for Python 2 and 3.)


Version 0.6
-----------

Released on 2012-02-29.

* *Backward incompatible*: completely change the Python API. See the
  documentation:
  https://weasyprint.readthedocs.io/en/latest/tutorial.html#as-a-python-library
* *Backward incompatible*: Proper margin collapsing.
  This changes how blocks are rendered: adjoining margins "collapse"
  (their maximum is used) instead of accumulating.
* Support images in ``embed`` or ``object`` elements.
* Switch to pystacia instead of PIL for raster images
* Add compatibility with CPython 2.6 and 3.2. (Previously only 2.7
  was supported)
* Many bug fixes


Version 0.5
-----------

Released on 2012-02-08.

* Support for the ``overflow`` and ``clip`` properties.
* Support for the ``opacity`` property from CSS3 Colors.
* Support for CSS 2D Transforms. These are prefixed, so you need to use
  ``-weasy-transform`` and ``-weasy-transform-origin``.


Version 0.4
-----------

Released on 2012-02-07.

* Support ``text-align: justify``, ``word-spacing`` and ``letter-spacing``.
* Partial support for CSS3 Paged Media: page size and margin boxes with
  page-based counters.
* All CSS 2.1 border styles
* Fix SVG images with non-pixel units. Requires CairoSVG 0.3
* Support for ``page-break-before`` and ``page-break-after``, except for
  the value ``avoid``.
* Support for the ``background-clip``, ``background-origin`` and
  ``background-size`` from CSS3 (but still with a single background
  per element)
* Support for the ``image-rendering`` from SVG. This one is prefixed,
  use ``-weasy-image-rendering``. It only has an effect on PNG output.


Version 0.3.1
-------------

Released on 2011-12-14.

Compatibility with CairoSVG 0.1.2


Version 0.3
-----------

Released on 2011-12-13.

* **Backward-incompatible change:** the 'size' property is now prefixed (since
  it is in an experimental specification). Use '-weasy-size' instead.
* cssutils 0.9.8 or higher is now required.
* Support SVG images with CairoSVG
* Support generated content: the ``:before`` and ``:after`` pseudo-elements,
  the ``content``, ``quotes`` and ``counter-*`` properties.
* Support ordered lists: all CSS 2.1 values of the ``list-style-type`` property.
* New user-agent stylesheet with HTML 5 elements and automatic quotes for many
  languages. Thanks Peter Moulder!
* Disable cssutils validation warnings, they are redundant with WeasyPrint’s.
* Add ``--version`` to the command-line script.
* Various bug fixes


Version 0.2
-----------

Released on 2011-11-25.

* Support for tables.
* Support the `box-sizing` property from CSS 3 Basic User Interface
* Support all values of vertical-align except top and bottom. They are
  interpreted as text-top and text-bottom.
* Minor bug fixes

Tables have some limitations:
Only the fixed layout and separate border model are supported.
There are also no page break inside tables so a table higher
than a page will overflow.


Version 0.1
-----------

Released on 2011-10-28.

First packaged release. Supports "simple" CSS 2.1 pages: there is no
support for floats, tables, or absolute positioning. Other than that
most of CSS 2.1 is supported, as well as CSS 3 Colors and Selectors.
