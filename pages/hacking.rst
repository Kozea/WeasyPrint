Documentation
=============

* `Installing </install/>`_
* `Using </using/>`_
* **Hacking**

Hacking WeasyPrint
~~~~~~~~~~~~~~~~~~

Assuming you already have the `dependencies </install/>`_, install the
`development version  <https://github.com/Kozea/WeasyPrint>`_ of WeasyPrint:

.. code-block:: sh

    git clone git://github.com/Kozea/WeasyPrint.git
    cd WeasyPrint
    source $MY_VIRTUALENV/bin/activate
    pip install -r test_requirements

This will install WeasyPrint in “editable” mode (which means that you don’t
need to re-install it every time you make a change in the source code) as
well as the additional dependencies for the test suite: PyPNG and Attest.

Use the ``attest`` command from the ``WeasyPrint`` directory to run the
test suite.

**TODO:** How to report bugs/feature requests (on `Redmine
<http://redmine.kozea.fr/projects/weasyprint/issues>`_) and submit
patches/pull requests (on `Github <https://github.com/Kozea/WeasyPrint>`_).

Dive into the source
--------------------

Much like `in web browsers
<http://www.html5rocks.com/en/tutorials/internals/howbrowserswork/#The_main_flow>`_,
the rendering of a document in WeasyPrint goes like this:

1. The HTML document is fetched and parsed into a DOM tree
2. CSS stylesheets (either found in the HTML or supplied by the user) are
   fetched and parsed
3. The stylesheets are applied to the DOM tree
4. The DOM tree with styles is transformed into a *formatting structure* made
   of rectangular boxes.
5. These boxes are *laid-out* with fixed dimensions and position onto pages
6. Finally, the pages are drawn in a PDF file

**TODO:** Explain the various parts of the code and how they match the steps
above.
