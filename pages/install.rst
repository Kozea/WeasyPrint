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
WeasyPrint 0.13 depends on:

* CPython_ 2.6, 2.7 or 3.2
* Pango_
* pycairo_ (cairo >= 1.12 works best but older versions are fine)
* Either:

  - PyGObject_ 3.x with cairo bindings.
    In this case Pango needs to be >= 1.29.3 and have introspection enabled.
  - PyGTK_. This only work on Python 2.x and installs all of GTK,
    but is available on more platforms. In this case you don’t need to
    install Pango or pycairo explicitly as PyGTK depends on them.

* lxml_
* Pystacia_
* tinycss_ >= 0.2
* cssselect_ >= 0.6
* CairoSVG_ >= 0.4.1
* Optional but recommended: virtualenv_

.. _CPython: http://www.python.org/
.. _Pango: http://www.pango.org/
.. _pycairo: http://cairographics.org/pycairo/
.. _PyGObject: https://live.gnome.org/PyGObject
.. _PyGTK: http://www.pygtk.org/
.. _lxml: http://lxml.de/
.. _Pystacia: http://liquibits.bitbucket.org/
.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/
.. _CairoSVG: http://cairosvg.org/
.. _virtualenv: http://www.virtualenv.org/


We recommend that you install ImageMagick (used by Pystacia), pycairo, Pango
and PyGObject/PyGTK with your distribution’s packages (see below) and
everything else with pip_.

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

.. [#] Symbolic links to the system packages in the virtualenv’s
       ``site-packages`` directory should work.

Debian Wheezy or Ubuntu 12.04
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: sh

    sudo apt-get install imagemagick python-cairo gir1.2-pango-1.0 python-gi python-gi-cairo


Ubuntu 11.10
~~~~~~~~~~~~

``python-gi`` is named ``python-gobject`` instead:

.. code-block:: sh

    sudo apt-get install imagemagick python-cairo gir1.2-pango-1.0 python-gobject python-gobject-cairo

Debian Squeeze, Ubuntu 11.04 or older
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PyGObject 3 is not available or Pango not recent enough for introspection,
use PyGTK instead:

.. code-block:: sh

    sudo apt-get install imagemagick python-gtk2

Mac OS X
~~~~~~~~

With Macports:

.. code-block:: sh

    sudo port install ImageMagick pango py27-gobject3 py27-cairo

`As of this writing <https://github.com/mxcl/homebrew/issues/12901>`_,
Homebrew has no package for PyGObject 3. Use PyGTK:

.. code-block:: sh

    brew install imagemagick pygtk

Windows
~~~~~~~

See `Anthony Plunkett’s blog <http://www.thefort.org/a/installing-weasyprint-on-windows/>`_.
Note however that 0.13 is buggy and won’t work on Windows. Until 0.14 is out, use the
`git version <https://github.com/Kozea/WeasyPrint/>`_