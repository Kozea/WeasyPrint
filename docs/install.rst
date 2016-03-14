Installing
==========

WeasyPrint |version| depends on:

* CPython_ 2.6, 2.7 or ≥ 3.2
* cairo_ [#]_
* Pango_
* CFFI_ ≥ 0.5
* lxml_ ≥ 3.0
* html5lib_ ≥ 0.99
* cairocffi_ ≥ 0.3
* tinycss_ = 0.3
* cssselect_ ≥ 0.6
* CairoSVG_ ≥ 1.0.20
* Pyphen_ ≥ 0.8
* Optional: GDK-PixBuf_ [#]_

.. _CPython: http://www.python.org/
.. _cairo: http://cairographics.org/
.. _Pango: http://www.pango.org/
.. _CFFI: https://cffi.readthedocs.org/
.. _html5lib: http://html5lib.readthedocs.org/
.. _cairocffi: http://pythonhosted.org/cairocffi/
.. _GTK+: http://www.gtk.org/
.. _lxml: http://lxml.de/
.. _tinycss: http://packages.python.org/tinycss/
.. _cssselect: http://packages.python.org/cssselect/
.. _CairoSVG: http://cairosvg.org/
.. _Pyphen: https://github.com/Kozea/Pyphen
.. _GDK-PixBuf: https://live.gnome.org/GdkPixbuf


Python, cairo, Pango and GDK-PixBuf need to be installed separately.
See :ref:`platform-specific instructions <platforms>` below.

CFFI and lxml can be installed by pip automatically
if your system has a C compiler and the recursive dependencies,
but using a system package might be easier.

Install WeasyPrint with pip_.
This will automatically install most of dependencies.
You probably need either virtualenv_ [#]_ (recommended) or using ``sudo``.

.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://pip-installer.org/

.. code-block:: sh

    virtualenv --system-site-packages ./venv
    . ./venv/bin/activate
    pip install WeasyPrint

Now let’s try it:

.. code-block:: sh

    weasyprint --help
    weasyprint http://weasyprint.org ./weasyprint-website.pdf

You should see warnings about unsupported CSS 3 stuff; this is expected.
In the PDF you should see the WeasyPrint logo on the first page.

You can also play with :ref:`navigator`:\ . Start it with:

.. code-block:: sh

    python -m weasyprint.navigator

… and open your browser at http://127.0.0.1:5000/. Read more :ref:`in the tutorial <navigator>`.

If everything goes well, you’re ready to :doc:`start using </tutorial>`
WeasyPrint! Otherwise, please copy the full error message and
`report the problem <http://weasyprint.org/community/>`_.

.. [#] cairo ≥ 1.12 is best but older versions should work too.
       The test suite passes on cairo 1.8 and 1.10 with some tests marked as
       “expected failures” due to behavior changes or bugs in cairo.

.. [#] Without it, PNG and SVG are the only supported image format:
       JPEG, GIF and others are not available.
       Versions before 0.22 were part of `GTK+`_.

.. [#] Passing the ``--system-site-packages`` option to virtualenv
       allows the environment to use the system packages for lxml or CFFI,
       but this is not necessary if you install them with pip.


.. _platforms:

By platform
-----------

Pango, GdkPixbuf, and cairo can not be installed
with pip and need to be installed from your platform’s packages.
lxml and CFFI can, but you’d still need their own dependencies.
This section lists system packages for lxml or CFFI when available,
the dependencies otherwise.
lxml needs *libxml2* and *libxslt*, CFFI needs *libffi*.
On Debian, the package names with development files are
``libxml2-dev``, ``libxslt1-dev`` and ``libffi-dev``.

If your favorite system is not listed here but you know the package names,
`tell us <http://weasyprint.org/community/>`_ so we can add it here.


Debian / Ubuntu
~~~~~~~~~~~~~~~

Debian 7.0 Wheezy or newer, Ubuntu 11.10 Oneiric or newer:

.. code-block:: sh

    sudo apt-get install python-dev python-pip python-lxml libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info


Debian 6.0 Squeeze, Ubuntu 10.04 Lucid:
GDK-PixBuf is part of GTK+, which also depends on cairo and Pango.

.. code-block:: sh

    sudo apt-get install python-dev python-pip python-lxml libgtk2.0-0 libffi-dev

Fedora
~~~~~~

.. code-block:: sh

    sudo yum install redhat-rpm-configrpm python-devel python-pip python-lxml cairo pango gdk-pixbuf2 libffi-devel

Archlinux
~~~~~~~~~

.. code-block:: sh

    sudo pacman -S python-pip python-lxml cairo pango gdk-pixbuf2


Gentoo
~~~~~~

.. code-block:: sh

    emerge weasyprint


Mac OS X
~~~~~~~~

With Macports

.. code-block:: sh

    sudo port install py27-pip py27-lxml cairo pango gdk-pixbuf2 libffi

With Homebrew:

.. code-block:: sh

    brew install python cairo pango gdk-pixbuf libxml2 libxslt libffi


Windows
~~~~~~~

* Get CPython 2.7 `from python.org <http://www.python.org/download/>`_,
* `Christoph Gohlke’s unofficial binaries
  <http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml>`_ for CFFI and lxml,
* and `Alexander Shaduri’s GTK+ installer
  <http://gtk-win.sourceforge.net/home/index.php/Main/Downloads>`_.
  Make sure that *Set up PATH environment variable* checked.
