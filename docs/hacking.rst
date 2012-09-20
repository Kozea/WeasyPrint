Hacking WeasyPrint
==================

Assuming you already have the :doc:`dependencies </install>`,
install the `development version`_ of WeasyPrint:

.. _development version: https://github.com/Kozea/WeasyPrint

.. code-block:: sh

    git clone git://github.com/Kozea/WeasyPrint.git
    cd WeasyPrint
    virtualenv --system-site-packages env
    . env/bin/activate
    pip install pytest
    pip install -e .
    weasyprint --help

This will install WeasyPrint in “editable” mode (which means that you don’t
need to re-install it every time you make a change in the source code) as
well as `py.test <http://pytest.org/>`_.

Use the ``py.test`` command from the ``WeasyPrint`` directory to run the
test suite.

Please report any bugs/feature requests and submit patches/pull requests
`on Github <https://github.com/Kozea/WeasyPrint>`_.


Dive into the source
--------------------

The rest of this document is a high-level overview of WeasyPrint’s source
code. For more details, see the various docstrings or even the code itself.
When in doubt, don’t hesitate to `ask <http://weasyprint.org/community>`_!

Much like `in web browsers
<http://www.html5rocks.com/en/tutorials/internals/howbrowserswork/#The_main_flow>`_,
the rendering of a document in WeasyPrint goes like this:

1. The HTML document is fetched and parsed into a DOM tree
2. CSS stylesheets (either found in the HTML or supplied by the user) are
   fetched and parsed
3. The stylesheets are applied to the DOM tree
4. The DOM tree with styles is transformed into a *formatting structure* made of rectangular boxes.
5. These boxes are *laid-out* with fixed dimensions and position onto pages.
6. The boxes are re-ordered to observe stacking rules.
7. The pages are drawn in a PDF file through a cairo surface.
8. Cairo’s PDF is modified to add metadata such as bookmarks and hyperlinks.

Documents
.........

WeasyPrint’s “entry point” is the ``Document`` class. An instance handles
a document for all of its lifetime. It is responsible of calling other parts
of the code for each step listed above.

The document is lazy: the various steps of the rendering are only done
when required (ie. when relevant attributes are accessed.)

HTML
....

Not much to see here. lxml.html_ handles step 1 and gives a *DOM tree*.
The lxml API is not actually DOM, but we’ll call it that anyway. The lxml
object for the root element (usually ``<html>``) is stored as the ``dom``
attribute of the document.

.. _lxml.html: http://lxml.de/lxmlhtml.html

CSS
...

Steps 2 and 3 happen in the ``weasyprint.css`` package. CSS stylesheets are
parsed with cssutils_. ``@import`` and ``@media`` rules are resolved to find
applicable rule sets. Then the ``weasyprint.css.validation`` module filters out
declarations with properties unknown to or unsupported by WeasyPrint or with
illegal or unsupported values.


.. _cssutils: http://cthedot.de/cssutils/
.. _lxml.cssselect: http://lxml.de/cssselect.html

As well as validation, several transformations are made at or around
this point:

* Shorthand properties are expanded. For example, ``margin`` is replaced by
  ``margin-top``, ``margin-right``, ``margin-bottom`` and ``margin-left``.
* Some values are simplified. They come as a list as a list of cssutils
  `Value objects`_. For example, keyword values are replaced by simple
  strings and the list is dropped when its length is always one for a given
  property.
* Hyphens in property names are replaced by underscores (``margin-top``
  becomes ``margin_top``) so that they can be used as Python attribute names
  later on.

.. _Value objects: http://packages.python.org/cssutils/docs/css.html#values

After that, the cascade_ (that’s the C in CSS!), together with inhertance
and initial values, assigns a value for each property to each DOM element.
These values are *computed* in ``weasyprint.css.computed_values``: lengths
are converted to pixels, etc. The objects representing the values are
simplified further: pixel length are simple floating points numbers.
Some values however are still cssutils objects to avoid ambiguities (eg.
percentages.)

.. _cascade: http://www.w3.org/TR/CSS21/cascade.html

Finally, the computed style for all DOM elements is stored in the
``computed_styles`` attribute of the document object.

Formatting structure
....................

The `visual formatting model`_ explains how *elements* (from the DOM tree)
generate *boxes* (in the formatting structure). This is step 4 above.
Boxes may have children and thus form a tree, much like elements. This tree
is generally close but not identical to the DOM tree: some elements generate
no or more than one box.

.. _visual formatting model: http://www.w3.org/TR/CSS21/visuren.html

Boxes are of a lot of different kinds. For example you should not confuse
*block-level boxes* and *block containers*, though *block boxes* are both.
The ``weasyprint.formatting_structure.boxes`` module has a whole hierarchy of
classes to represent all these boxes. We won’t go into the details here, see
the module and class docstrings.

The ``weasyprint.formatting_structure.build`` module takes a DOM tree with
associated computed styles, and builds a formatting structure. It generates
the right boxes for each element and ensures they conform to the models rules.
(Eg. an inline box can not contain a block.) Each box has a ``some_box.style``
attribute containing computed values for each known CSS property.

The main logic is based on the ``display`` property, but it can be overridden for some elements by adding a handler in the ``weasyprint.html`` module.
This is how ``<img>`` and ``<td colspan=3>`` are currently implemented,
for example.
This module is rather short as most of HTML is defined in CSS rather than
in Python, in the `user agent stylesheet`_.

The box for the root element (and, through its ``children`` attribute, the
whole tree) is set to the ``formatting_structure`` attribute of the document.

.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css

Layout
......

Step 5 is the layout. You could say the everything else is glue code and
this is where the magic happens.

During the layout the document’s content is … laid out on pages. This is when
we decide where to do line breaks and page breaks. If a break happens inside
of a box, that box is split into two (or more) boxes in the layout result.

According to the `box model`_, each box has rectangular margin, border,
padding and content areas:

.. _box model: http://www.w3.org/TR/CSS21/box.html

.. image:: http://www.w3.org/TR/CSS21/images/boxdim.png
    :align: center

While ``box.style`` contains computed values, the `used values`_ are set
as attributes of the ``Box`` object itself during the layout. This
include resolving percentages and especially ``auto`` values into absolute,
pixel lengths. Once the layout done, each box has used values for
margins, border width, padding of each four sides, as well as the ``width``
and ``height`` of the content area. They also have ``position_x`` and
``position_y``, the absolute coordinates of the top-left corner of the
margin box (**not** the content box) from the top-left corner of the page.

.. _used values: http://www.w3.org/TR/CSS21/cascade.html#used-value

Boxes also have helpers methods such as ``content_box_y()`` and
``margin_width()`` that give other metrics that can be useful in various
parts of the code.

When the layout is done, a list of ``PageBox`` objects is set to the
``pages`` attribute of the document.

Stacking
........

In step 6, the boxes are reorder by the ``weasyprint.stacking`` module
to observe `stacking rules`_ such as the ``z-index`` property.
The result is a tree of `stacking contexts`.

.. _stacking rules: http://www.w3.org/TR/CSS21/zindex.html

Drawing
.......

Next, in step 7, each laid-out page is *drawn* onto a cairo_ surface.
Since each box has absolute coordinates on the page from the layout step,
the logic here should be minimal. If you find yourself adding a lot of logic
here, maybe it should go in the layout or stacking instead.

The code lives in the ``weasyprint.draw`` module and is called by the
``write_to`` method of the document.

.. _cairo: http://cairographics.org/pycairo/

Metadata
........

Finally (step 8), the ``weasyprint.pdf`` parses the PDF file produced by cairo
and makes an *incremental update* to add internal and external hyperlinks,
as well as outlines / bookmarks.
