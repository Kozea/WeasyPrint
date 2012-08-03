Documentation
=============

* **Installing**
* `Using </using/>`_
* `Hacking </hacking/>`_
* `Features </features/>`_

Source code
-----------

The git repository is :codelink:`on GitHub` and releases tarballs are
`on PyPI <http://pypi.python.org/pypi/WeasyPrint>`_, but these are not
the recommended way of installing.

Installing WeasyPrint
---------------------

WeasyPrint has been packaged for some Linux distributions:

* **Archlinux**, in the AUR: `python-weasyprint`_ (for Python 3) or
  `python2-weasyprint`_ (for Python 2, installs the command-line script
  as ``weasyprint2``).
* **Gentoo**: in the `Kozea overlay`_

(Please do `tell us`_ if you make such a package!)

.. _python-weasyprint: https://aur.archlinux.org/packages.php?ID=57205
.. _python2-weasyprint: https://aur.archlinux.org/packages.php?ID=57201
.. _Kozea overlay: https://github.com/Kozea/Overlay/blob/master/README
.. _tell us: /community/


For other distributions or if you want to install it yourself,
WeasyPrint 0.14 depends on:

* CPython_ 2.6, 2.7 or 3.2
* Either:

  - PyGTK_ and its dependencies.
    This is available in more distributions but only works on Python 2.x
    and requires the whole GTK+ stack.
  - Pango_ >= 1.29.3, pycairo_ and GdkPixbuf_ >= 2.25\ [#]_
    with introspection data for each, as well as PyGObject_ 3.x.
    This works on all supported Python version and is lighter on dependencies,
    but requires fairly recent versions.

* lxml_
* Pystacia_
* tinycss_ >= 0.2
* cssselect_ >= 0.6
* CairoSVG_ >= 0.4.1

cairo >= 1.12 is best but older versions should work too.\ [#]_

.. _CPython: http://www.python.org/
.. _Pango: http://www.pango.org/
.. _pycairo: http://cairographics.org/pycairo/
.. _GdkPixbuf: https://live.gnome.org/GdkPixbuf
.. _PyGObject: https://live.gnome.org/PyGObject
.. _PyGTK: http://www.pygtk.org/
.. _lxml: http://lxml.de/
.. _Pystacia: http://liquibits.bitbucket.org/
.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/
.. _CairoSVG: http://cairosvg.org/


We recommend that you install PyGTK (or Pango, GdkPixbuf, pycairo and
PyGObject) and lxml\ [#]_ with your distribution’s packages (see below)
and everything else in a virtualenv_ with pip_.

.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://pip-installer.org/

With virtualenv you’ll need ``--system-site-packages`` or some other
workaround\ [#]_ as pycairo and some others can not be installed with
pip. Installing WeasyPrint will also pull the remaining dependencies.

.. code-block:: sh

    virtualenv --system-site-packages ./venv
    . ./venv/bin/activate
    pip install WeasyPrint
    weasyprint --help

Now let’s try it:

.. code-block:: sh

    weasyprint http://weasyprint.org ./weasyprint-website.pdf

You should see warnings about unsupported CSS 3 stuff, this is expected.
In the PDF you should see the WeasyPrint logo on the first page.

If everything goes well, you’re ready to `start using </using/>`_ WeasyPrint!
Otherwise, please copy the full error message and `report the problem
</community/>`_.

.. [#] GdkPixbuf is actually optional. Without it, PNG is the only
       supported raster image format: JPEG, GIF and others are not available.

.. [#] The test suite passes on cairo 1.8 and 1.10 with some tests marked as
       “expected failures” due to bugs or behavior changes in cairo.

.. [#] Alternatively, install lxml with pip but make sure you have libxml2
       and libxslt with development headers to compile it. On Debian
       the package are named `libxml2-dev` and `libxslt1-dev`.

.. [#] Symbolic links to the system packages in the virtualenv’s
       ``site-packages`` directory should work.


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
