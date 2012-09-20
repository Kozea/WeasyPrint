Installing
==========

WeasyPrint |version| depends on:

* CPython_ 2.6, 2.7 or 3.2
* Either:

  - PyGTK_ and its dependencies.
    This is available in more distributions but only works on Python 2.x
    and requires the whole GTK+ stack.
  - Pango_ ≥ 1.29.3, pycairo_\ [#]_ and GdkPixbuf_ ≥ 2.25\ [#]_
    with introspection data for each, as well as PyGObject_ 3.x.
    This works on all supported Python version and is lighter on dependencies,
    but requires fairly recent versions.

* lxml_
* tinycss_ = 0.3
* cssselect_ ≥ 0.6
* CairoSVG_ ≥ 0.4.1\ [#]_

.. _CPython: http://www.python.org/
.. _Pango: http://www.pango.org/
.. _pycairo: http://cairographics.org/pycairo/
.. _GdkPixbuf: https://live.gnome.org/GdkPixbuf
.. _PyGObject: https://live.gnome.org/PyGObject
.. _PyGTK: http://www.pygtk.org/
.. _lxml: http://lxml.de/
.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/
.. _CairoSVG: http://cairosvg.org/


**First**, install C dependencies with your platform’s packages
(:ref:`see below  <platforms>`). Then install WeasyPrint with pip_
in a virtualenv_. This will automatically install the remaining dependencies.
With virtualenv you’ll need ``--system-site-packages``\ [#]_ since pycairo
and some others can not be installed with pip.

.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://pip-installer.org/

.. code-block:: sh

    virtualenv --system-site-packages ./venv
    . ./venv/bin/activate
    pip install WeasyPrint
    weasyprint --help

Now let’s try it:

.. code-block:: sh

    weasyprint http://weasyprint.org ./weasyprint-website.pdf

You should see warnings about unsupported CSS 3 stuff; this is expected.
In the PDF you should see the WeasyPrint logo on the first page.

You can also play with :ref:`navigator`:

.. code-block:: sh

    python -m weasyprint.navigator

If everything goes well, you’re ready to :doc:`start using </using>`
WeasyPrint! Otherwise, please copy the full error message and
`report the problem <http://weasyprint.org/community/>`_.

.. [#] cairo ≥ 1.12 is best but older versions should work too.
       The test suite passes on cairo 1.8 and 1.10 with some tests marked as
       “expected failures” due to bugs or behavior changes in cairo.

.. [#] GdkPixbuf is actually optional. Without it, PNG is the only
       supported raster image format: JPEG, GIF and others are not available.

.. [#] CairoSVG is actually optional. Without it, SVG images are not supported.

.. [#] … or some other workaround. Symbolic links to the system packages
       in the virtualenv’s ``site-packages`` directory should work.


.. _platforms:

By platform
-----------

PyGTK (or Pango, GdkPixbuf, pycairo and PyGObject) can not be installed
with pip and need to be installed from your platform’s packages.
lxml can\ [#]_, but pre-compiled packages are often easier.


.. [#] In this case you additionally need libxml2 and libxslt with
       development headers to compile lxml. On Debian the package are named
       ``libxml2-dev`` and ``libxslt1-dev``.


Debian / Ubuntu
~~~~~~~~~~~~~~~

With PyGTK (Python 2 only):

.. code-block:: sh

    sudo apt-get install python-gtk2 python-lxml

… or with PyGObject (Debian Wheezy, Ubuntu 12.04 Precise or more recent)
on Python 2:

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 gir1.2-gdkpixbuf-2.0 python-gi-cairo python-lxml

On Python 3:

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 gir1.2-gdkpixbuf-2.0 python3-gi-cairo python3-lxml


Archlinux
~~~~~~~~~

WeasyPrint itself is packaged in the AUR: `python-weasyprint`_ (for Python 3)
or `python2-weasyprint`_ (for Python 2, installs the command-line script
as ``weasyprint2``).

.. _python-weasyprint: https://aur.archlinux.org/packages.php?ID=57205
.. _python2-weasyprint: https://aur.archlinux.org/packages.php?ID=57201


Gentoo
~~~~~~

WeasyPrint itself is packaged in the `Kozea overlay
<https://github.com/Kozea/Overlay/blob/master/README>`_.


Mac OS X
~~~~~~~~

With Macports (adjust the ``py27`` part for other Python versions),
with PyGTK:

.. code-block:: sh

    sudo port install py27-gtk py27-lxml

… or with PyGObject:

.. code-block:: sh

    sudo port install pango gdk-pixbuf2 py27-gobject3 py27-cairo py27-lxml

With Homebrew:

.. code-block:: sh

    brew install pygtk libxml2 libxslt

As of this writing Homebrew has no package
`for PyGObject 3 <https://github.com/mxcl/homebrew/issues/12901>`_ or
`for lxml <https://github.com/mxcl/homebrew/wiki/Acceptable-Formula>`_.
Use PyGTK and install lxml’s own dependencies. lxml itself will be installed
automatically when you run ``pip install WeasyPrint``.


Windows
~~~~~~~

Assuming you already have `Python <http://www.python.org/download/>`_
2.6 or 2.7, the easiest is to use Christoph Gohlke’s
`lxml unofficial binaries <http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml>`_
and the `PyGTK all-in-one installer <http://www.pygtk.org/downloads.html>`_.

Be careful and see the `README
<http://ftp.gnome.org/pub/GNOME/binaries/win32/pygtk/2.24/pygtk-all-in-one.README>`_
if you had anything GTK-related already installed.
