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

* Archlinux, in the AUR: `python-weasyprint`_ (for Python 3) or
  `python2-weasyprint`_ (for Python 2, installs the command-line script
  as ``weasyprint2``).
* Gentoo: in the `Kozea overlay`_

(Please do `tell us`_ if you make such a package!)

.. _python-weasyprint: https://aur.archlinux.org/packages.php?ID=57205
.. _python2-weasyprint: https://aur.archlinux.org/packages.php?ID=57201
.. _Kozea overlay: https://github.com/Kozea/Overlay/blob/master/README
.. _tell us: /community/


For other distributions or if you want to install it yourself,
WeasyPrint 0.11 depends on:

.. Note: keep this in sync with setup.py

* CPython 2.6, 2.7 or 3.2
* Pango **>= 1.29.3** with GObject introspection
* PyGObject 3.x with cairo bindings
* pycairo
* lxml
* Pystacia
* tinycss >= 0.2
* cssselect >= 0.6
* CairoSVG >= 0.4.1

We recommend that you install Pango, PyGObject, pycairo, lxml and ImageMagick
(used by Pystacia) with your distribution’s packages.

For example, on Debian Wheezy or Ubuntu 12.04:

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 python-gi python-cairo python-gi-cairo python-lxml imagemagick

On Ubuntu 11.10, ``python-gi`` is named ``python-gobject`` instead:

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 python-gobject python-cairo python-gobject-cairo python-lxml imagemagick

**For OS X** you may have to build Pango with introspection and PyGObject 3
yourself from source as they are not yet in MacPorts or Homebrew. See the
`progress on our bug tracker <http://redmine.kozea.fr/issues/823>`_.

Then, create a `virtualenv`_. You’ll need ``--system-site-packages`` or
some other workaround\ [#]_ as PyGObject and pycairo can not be installed
with pip. Installing WeasyPrint will also pull other Python dependencies.

.. _virtualenv: http://www.virtualenv.org/

.. code-block:: sh

    virtualenv --system-site-packages $PATH_TO_VENV
    . $PATH_TO_VENV/bin/activate
    pip install WeasyPrint
    weasyprint --help

If everything goes well, you’re ready to `start using </using/>`_ WeasyPrint!
Otherwise, please copy the exact error message and `report the problem
</community/>`_.

.. [#] Symbolic links to the system packages in the virtualenv’s
       ``site-packages`` directory should work.
