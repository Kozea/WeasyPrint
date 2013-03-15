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
    pip install pytest Sphinx -e .
    weasyprint --help

This will install WeasyPrint in “editable” mode
(which means that you don’t need to re-install it
every time you make a change in the source code)
as well as `py.test <http://pytest.org/>`_
and `Sphinx <http://sphinx.pocoo.org/>`_.


Documentation changes
---------------------

The documentation lives in the ``docs`` directory,
but API section references docstrings in the source code.
Run ``python setup.py build_sphinx`` to rebuild the documentation
and get the output in ``docs/_build/html``.
The website version is updated automatically when we push to master on GitHub.


Code changes
------------

Use the ``py.test`` command from the ``WeasyPrint`` directory to run the
test suite.

Please report any bugs/feature requests and submit patches/pull requests
`on Github <https://github.com/Kozea/WeasyPrint>`_.


Dive into the source
--------------------

The rest of this document is a high-level overview of WeasyPrint’s source
code. For more details, see the various docstrings or even the code itself.
When in doubt, feel free to `ask <http://weasyprint.org/community>`_!

Much like `in web browsers
<http://www.html5rocks.com/en/tutorials/internals/howbrowserswork/#The_main_flow>`_,
the rendering of a document in WeasyPrint goes like this:

1. The HTML document is fetched and parsed into a tree of elements (like DOM)
2. CSS stylesheets (either found in the HTML or supplied by the user) are
   fetched and parsed
3. The stylesheets are applied to the DOM tree
4. The DOM tree with styles is transformed into a *formatting structure* made of rectangular boxes.
5. These boxes are *laid-out* with fixed dimensions and position onto pages.
6. The boxes are re-ordered to observe stacking rules.
7. The pages are drawn in a PDF file through a cairo surface.
8. Cairo’s PDF is modified to add metadata such as bookmarks and hyperlinks.


HTML
....

Not much to see here. The :class:`weasyprint.HTML` class is a thin wrapper
around lxml.html_ which handles step 1 and gives a tree of HTML *elements*.
Although the actual API is different, this tree is conceptually the same
as what web browsers call *the DOM*.

.. _lxml.html: http://lxml.de/lxmlhtml.html


CSS
...

As with HTML, CSS stylesheets are parsed in the :class:`weasyprint.CSS` class
with an external library, tinycss_.
After the In addition to the actual parsing, the :mod:`weasyprint.css` and
:mod:`weasyprint.css.validation` modules do some pre-processing:

* Unknown and unsupported declarations are ignored with warnings.
  Remaining property values are parsed in a property-specific way
  from raw tinycss tokens into a higher-level form.
* Shorthand properties are expanded. For example, ``margin`` becomes
  ``margin-top``, ``margin-right``, ``margin-bottom`` and ``margin-left``.
* Hyphens in property names are replaced by underscores (``margin-top``
  becomes ``margin_top``) so that they can be used as Python attribute names
  later on. This transformation is safe since none for the know (not ignored)
  properties have an underscore character.
* Selectors are pre-compiled with cssselect_.

.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/


The cascade
...........

After that and still in the :mod:`weasyprint.css` package, the cascade_
(that’s the C in CSS!) applies the stylesheets to the element tree.
Selectors associate property declarations to elements. In case of conflicting
declarations (different values for the same property on the same element),
the one with the highest *weight* wins. Weights are based on the stylesheet’s
:ref:`origin <stylesheet-origins>`, ``!important`` markers, selector
specificity and source order. Missing values are filled in through
*inheritance* (from the parent element) or the property’s *initial value*,
so that every element has a *specified value* for every property.

.. _cascade: http://www.w3.org/TR/CSS21/cascade.html

These *specified values* are turned into *computed values* in the
``weasyprint.css.computed_values`` module. Keywords and lengths in various
units are converted to pixels, etc. At this point the value for some
properties can be represented by a single number or string, but some require
more complex objects. For example, a :class:`Dimension` object can be either
an absolute length or a percentage.

The final result of the :func:`~weasyprint.css.get_all_computed_styles`
function is a big dict where keys are ``(element, pseudo_element_type)``
tuples, and keys are :obj:``StyleDict`` objects. Elements are lxml objects,
while the type of pseudo-element is a string for eg. ``::first-line``
selectors, or :obj:`None` for “normal” elements. :obj:`StyleDict` objects
are dicts with attribute access mapping property names to the computed values.
(The return value is not the dict itself, but a convenience :func:`style_for`
function for accessing it.)


Formatting structure
....................

The `visual formatting model`_ explains how *elements* (from the lxml tree)
generate *boxes* (in the formatting structure). This is step 4 above.
Boxes may have children and thus form a tree, much like elements. This tree
is generally close but not identical to the lxml tree: some elements generate
more than one box or none.

.. _visual formatting model: http://www.w3.org/TR/CSS21/visuren.html

Boxes are of a lot of different kinds. For example you should not confuse
*block-level boxes* and *block containers*, though *block boxes* are both.
The :mod:`weasyprint.formatting_structure.boxes` module has a whole hierarchy
of classes to represent all these boxes. We won’t go into the details here,
see the module and class docstrings.

The :mod:`weasyprint.formatting_structure.build` module takes an lxml tree with
associated computed styles, and builds a formatting structure. It generates
the right boxes for each element and ensures they conform to the models rules.
(Eg. an inline box can not contain a block.) Each box has a :attr:`.style`
attribute containing the :class:`StyleDict` of computed values.

The main logic is based on the ``display`` property, but it can be overridden
for some elements by adding a handler in the ``weasyprint.html`` module.
This is how ``<img>`` and ``<td colspan=3>`` are currently implemented,
for example.
This module is rather short as most of HTML is defined in CSS rather than
in Python, in the `user agent stylesheet`_.

The :func:`~weasyprint.formatting_structure.build.build_formatting_structure`
function returns the box for the root element (and, through its
:attr:`children` attribute, the whole tree).

.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css


Layout
......

Step 5 is the layout. You could say the everything else is glue code and
this is where the magic happens.

During the layout the document’s content is, well, laid out on pages.
This is when we decide where to do line breaks and page breaks. If a break
happens inside of a box, that box is split into two (or more) boxes in the
layout result.

According to the `box model`_, each box has rectangular margin, border,
padding and content areas:

.. _box model: http://www.w3.org/TR/CSS21/box.html

.. image:: _static/box_model.png
    :align: center

While :obj:`box.style` contains computed values, the `used values`_ are set
as attributes of the :class:`Box` object itself during the layout. This
include resolving percentages and especially ``auto`` values into absolute,
pixel lengths. Once the layout done, each box has used values for
margins, border width, padding of each four sides, as well as the
:attr:`width` and :attr:`height` of the content area. They also have
:attr:`position_x`` and :attr:`position_y``, the absolute coordinates of the
top-left corner of the margin box (**not** the content box) from the top-left
corner of the page.\ [#]_

Boxes also have helpers methods such as :meth:`content_box_y` and
:meth:`margin_width` that give other metrics that can be useful in various
parts of the code.

The final result of the layout is a list of :class:`PageBox` objects.

.. [#] These are the coordinates *if* no `CSS transform`_ applies.
       Transforms change the actual location of boxes, but they are applies
       later during drawing and do not affect layout.
.. _used values: http://www.w3.org/TR/CSS21/cascade.html#used-value
.. _CSS transform: http://www.w3.org/TR/css3-transforms/


Stacking
........

In step 6, the boxes are reorder by the :mod:`weasyprint.stacking` module
to observe `stacking rules`_ such as the ``z-index`` property.
The result is a tree of *stacking contexts*.

.. _stacking rules: http://www.w3.org/TR/CSS21/zindex.html


Drawing
.......

Next, in step 7, each laid-out page is *drawn* onto a cairo_ surface.
Since each box has absolute coordinates on the page from the layout step,
the logic here should be minimal. If you find yourself adding a lot of logic
here, maybe it should go in the layout or stacking instead.

The code lives in the :mod:`weasyprint.draw` module.

.. _cairo: http://cairographics.org/pycairo/


Metadata
........

Finally (step 8), the :mod:`weasyprint.pdf` module parses the PDF file
produced by cairo and makes appends to it to add meta-data:
internal and external hyperlinks, as well as outlines / bookmarks.
